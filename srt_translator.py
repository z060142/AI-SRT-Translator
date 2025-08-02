#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import sys
import json
import time
import requests
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from datetime import datetime, timedelta
import threading
from typing import List, Dict, Tuple, Optional

class SRTEntry:
    def __init__(self, index: int, start_time: str, end_time: str, text: str):
        self.index = index
        self.start_time = start_time
        self.end_time = end_time
        self.text = text.strip()
        self.translated_text = ""
        
    def __str__(self):
        return f"{self.index}\n{self.start_time} --> {self.end_time}\n{self.text}\n"

class SRTParser:
    @staticmethod
    def parse_srt(content: str) -> List[SRTEntry]:
        entries = []
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
                
            try:
                index = int(lines[0])
                time_line = lines[1]
                text = '\n'.join(lines[2:])
                
                if ' --> ' in time_line:
                    start_time, end_time = time_line.split(' --> ')
                    entries.append(SRTEntry(index, start_time.strip(), end_time.strip(), text))
            except (ValueError, IndexError):
                continue
                
        return entries
    
    @staticmethod
    def entries_to_srt(entries: List[SRTEntry]) -> str:
        result = []
        for entry in entries:
            text = entry.translated_text if entry.translated_text else entry.text
            result.append(f"{entry.index}\n{entry.start_time} --> {entry.end_time}\n{text}\n")
        return '\n'.join(result)

class APITranslator:
    def __init__(self, api_url: str, model: str, api_key: str):
        self.api_url = api_url
        self.model = model
        self.api_key = api_key
        self.session = requests.Session()
        
    def translate_text(self, text: str, context: str = "") -> str:
        prompt = f"""請將以下英文字幕翻譯成繁體中文。要求：
1. 保持原文的語氣和情感
2. 不要翻譯專有名詞（人名、地名、品牌名等）
3. 保持字幕的簡潔性
4. 確保翻譯自然流暢

{f"前面的上下文參考：{context}" if context else ""}

需要翻譯的文本：
{text}

只回覆翻譯結果，不要包含其他說明："""

        # 檢查API URL是否正確
        if not self.api_url.endswith(('/v1/chat/completions', '/messages', '/chat/completions')):
            print(f"警告：API網址可能不正確: {self.api_url}")
            print("常見的API端點:")
            print("- OpenAI: https://api.openai.com/v1/chat/completions")
            print("- Claude: https://api.anthropic.com/v1/messages")
            print("- 自定義: 通常以 /v1/chat/completions 結尾")

        try:
            if "openai" in self.api_url.lower() or "api.openai.com" in self.api_url:
                return self._translate_openai(prompt)
            elif "anthropic" in self.api_url.lower() or "claude" in self.model.lower():
                return self._translate_anthropic(prompt)
            else:
                return self._translate_generic(prompt)
        except Exception as e:
            if "<!DOCTYPE html>" in str(e) or "HTML" in str(e):
                raise Exception(f"API網址返回HTML頁面而非JSON。請檢查API端點是否正確。當前網址: {self.api_url}")
            raise Exception(f"翻譯API調用失敗: {str(e)}")
    
    def _translate_openai(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        response = self.session.post(self.api_url, headers=headers, json=data, timeout=30)
        
        print(f"API響應狀態碼: {response.status_code}")
        print(f"API響應內容: {response.text[:200]}...")
        
        response.raise_for_status()
        
        if not response.text.strip():
            raise Exception("API返回空內容")
            
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    
    def _translate_anthropic(self, prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.3
        }
        
        response = self.session.post(self.api_url, headers=headers, json=data, timeout=30)
        
        print(f"Anthropic API響應狀態碼: {response.status_code}")
        print(f"Anthropic API響應內容: {response.text[:500]}...")
        
        response.raise_for_status()
        
        if not response.text.strip():
            raise Exception("API返回空內容")
            
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            raise Exception(f"API響應不是有效的JSON格式: {response.text[:200]}")
            
        return result["content"][0]["text"].strip()
    
    def _translate_generic(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        response = self.session.post(self.api_url, headers=headers, json=data, timeout=30)
        
        print(f"Generic API響應狀態碼: {response.status_code}")
        print(f"Generic API響應內容: {response.text[:500]}...")
        
        response.raise_for_status()
        
        if not response.text.strip():
            raise Exception("API返回空內容")
            
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            raise Exception(f"API響應不是有效的JSON格式: {response.text[:200]}")
            
        if "choices" in result:
            return result["choices"][0]["message"]["content"].strip()
        elif "content" in result:
            return result["content"][0]["text"].strip()
        else:
            raise Exception(f"不支援的API響應格式: {list(result.keys())}")

class BatchTranslator:
    def __init__(self, translator: APITranslator):
        self.translator = translator
        
    def count_words(self, text: str) -> int:
        return len(text.split())
    
    def create_batches(self, entries: List[SRTEntry], max_words: int = 100) -> List[List[SRTEntry]]:
        batches = []
        current_batch = []
        current_word_count = 0
        
        for entry in entries:
            entry_words = self.count_words(entry.text)
            
            if current_word_count + entry_words > max_words and current_batch:
                batches.append(current_batch)
                current_batch = [entry]
                current_word_count = entry_words
            else:
                current_batch.append(entry)
                current_word_count += entry_words
                
        if current_batch:
            batches.append(current_batch)
            
        return batches
    
    def get_context(self, all_entries: List[SRTEntry], current_start_idx: int) -> str:
        context_entries = []
        context_count = 0
        
        for i in range(max(0, current_start_idx - 10), current_start_idx):
            if all_entries[i].translated_text and context_count < 5:
                context_entries.append(all_entries[i].translated_text)
                context_count += 1
                
        return " ".join(context_entries[-5:]) if context_entries else ""
    
    def translate_batch(self, batch: List[SRTEntry], context: str = "") -> List[str]:
        batch_text = "\n\n".join([f"[{entry.index}] {entry.text}" for entry in batch])
        
        try:
            translated = self.translator.translate_text(batch_text, context)
            
            # 更強健的翻譯結果解析
            translated_lines = []
            lines = translated.split('\n')
            
            current_translation = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 如果是帶索引的行
                if line.startswith('[') and ']' in line:
                    # 保存前一個翻譯
                    if current_translation:
                        translated_lines.append(current_translation.strip())
                    # 開始新翻譯
                    current_translation = line.split(']', 1)[1].strip()
                else:
                    # 繼續當前翻譯
                    if current_translation:
                        current_translation += " " + line
                    else:
                        current_translation = line
            
            # 添加最後一個翻譯
            if current_translation:
                translated_lines.append(current_translation.strip())
            
            # 如果解析結果數量不匹配，嘗試按行分割
            if len(translated_lines) != len(batch):
                print(f"警告：翻譯結果數量不匹配 (期望{len(batch)}, 得到{len(translated_lines)})")
                print(f"原始翻譯內容: {translated}")
                
                # 備用解析：直接按非空行分割
                alt_lines = [line.strip() for line in translated.split('\n') if line.strip()]
                # 過濾掉可能的索引行
                alt_lines = [line.split(']', 1)[1].strip() if line.startswith('[') and ']' in line else line for line in alt_lines]
                
                if len(alt_lines) == len(batch):
                    translated_lines = alt_lines
                else:
                    print(f"備用解析也失敗，將對每個條目單獨翻譯")
                    return self.translate_individually(batch, context)
            
            # 確保數量匹配
            while len(translated_lines) < len(batch):
                translated_lines.append(f"[翻譯失敗] {batch[len(translated_lines)].text}")
                
            return translated_lines[:len(batch)]
            
        except Exception as e:
            print(f"批次翻譯失敗: {e}")
            print(f"將對此批次進行單獨翻譯")
            return self.translate_individually(batch, context)
    
    def translate_individually(self, batch: List[SRTEntry], context: str = "") -> List[str]:
        """對批次中的每個條目單獨翻譯"""
        results = []
        for entry in batch:
            try:
                translated = self.translator.translate_text(entry.text, context)
                results.append(translated.strip())
                print(f"單獨翻譯完成: [{entry.index}] {entry.text[:30]}...")
            except Exception as e:
                print(f"單獨翻譯失敗 [{entry.index}]: {e}")
                results.append(f"[翻譯失敗] {entry.text}")
        return results

class SRTTranslatorGUI:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("SRT字幕翻譯工具 - 批次處理")
        self.root.geometry("900x700")
        
        self.translator = None
        self.entries = []
        self.translated_entries = []
        self.batch_files = []  # 存儲批次檔案列表
        self.current_file_index = 0  # 當前處理的檔案索引
        
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        # 配置框架
        config_frame = ttk.LabelFrame(self.root, text="API配置", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # API URL
        ttk.Label(config_frame, text="API網址:").grid(row=0, column=0, sticky="w", pady=2)
        self.api_url_var = tk.StringVar(value="https://api.openai.com/v1/chat/completions")
        ttk.Entry(config_frame, textvariable=self.api_url_var, width=60).grid(row=0, column=1, sticky="ew", pady=2)
        
        # 模型
        ttk.Label(config_frame, text="模型:").grid(row=1, column=0, sticky="w", pady=2)
        self.model_var = tk.StringVar(value="gpt-3.5-turbo")
        ttk.Entry(config_frame, textvariable=self.model_var, width=60).grid(row=1, column=1, sticky="ew", pady=2)
        
        # API Key
        ttk.Label(config_frame, text="API Key:").grid(row=2, column=0, sticky="w", pady=2)
        self.api_key_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.api_key_var, width=60, show="*").grid(row=2, column=1, sticky="ew", pady=2)
        
        config_frame.columnconfigure(1, weight=1)
        
        # 按鈕框架
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(button_frame, text="保存配置", command=self.save_config).pack(side="left", padx=5)
        ttk.Button(button_frame, text="選擇檔案", command=self.select_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="清空檔案列表", command=self.clear_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="開始翻譯", command=self.start_translation).pack(side="left", padx=5)
        
        # 檔案列表框架
        files_frame = ttk.LabelFrame(self.root, text="待處理檔案列表", padding=10)
        files_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 檔案列表視窗
        list_frame = ttk.Frame(files_frame)
        list_frame.pack(fill="both", expand=True)
        
        self.files_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.files_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 拖拽區域
        drag_frame = ttk.LabelFrame(self.root, text="拖拽SRT檔案到此處", padding=20)
        drag_frame.pack(fill="x", padx=10, pady=5)
        
        self.drag_label = ttk.Label(drag_frame, text="將SRT檔案拖拽到此處\n或點擊上方按鈕選擇檔案\n支援批次處理", 
                                   font=("Arial", 12), foreground="gray")
        self.drag_label.pack(expand=True)
        
        # 拖拽綁定
        drag_frame.drop_target_register(DND_FILES)
        drag_frame.dnd_bind('<<Drop>>', self.on_drop)
        
        # 進度條
        self.progress_var = tk.StringVar(value="準備就緒")
        ttk.Label(self.root, textvariable=self.progress_var).pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(self.root, mode='determinate')
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        
    def load_config(self):
        config_file = "srt_translator_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_url_var.set(config.get('api_url', ''))
                    self.model_var.set(config.get('model', ''))
                    self.api_key_var.set(config.get('api_key', ''))
            except Exception as e:
                print(f"載入配置失敗: {e}")
    
    def save_config(self):
        config = {
            'api_url': self.api_url_var.get(),
            'model': self.model_var.get(),
            'api_key': self.api_key_var.get()
        }
        
        try:
            with open("srt_translator_config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", "配置已保存！")
        except Exception as e:
            messagebox.showerror("錯誤", f"保存配置失敗: {e}")
    
    def select_files(self):
        file_paths = filedialog.askopenfilenames(
            title="選擇SRT檔案",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
        )
        for file_path in file_paths:
            self.add_file_to_batch(file_path)
    
    def add_file_to_batch(self, file_path):
        if file_path not in self.batch_files:
            self.batch_files.append(file_path)
            filename = os.path.basename(file_path)
            self.files_listbox.insert(tk.END, filename)
            self.update_status_display()
    
    def clear_files(self):
        self.batch_files.clear()
        self.files_listbox.delete(0, tk.END)
        self.update_status_display()
    
    def update_status_display(self):
        count = len(self.batch_files)
        if count == 0:
            self.drag_label.config(text="將SRT檔案拖拽到此處\n或點擊上方按鈕選擇檔案\n支援批次處理")
            self.progress_var.set("準備就緒")
        else:
            self.drag_label.config(text=f"已選擇 {count} 個檔案\n支援批次處理")
            self.progress_var.set(f"已選擇 {count} 個檔案，準備翻譯")
    
    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        valid_files = [f for f in files if f.lower().endswith('.srt')]
        
        if valid_files:
            for file_path in valid_files:
                self.add_file_to_batch(file_path)
        else:
            messagebox.showerror("錯誤", "請選擇SRT檔案")
    
    def load_srt_file(self, file_path):
        """Legacy method for single file loading"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.entries = SRTParser.parse_srt(content)
            self.file_path = file_path
            
            self.drag_label.config(text=f"已載入: {os.path.basename(file_path)}\n共 {len(self.entries)} 個字幕條目")
            self.progress_var.set(f"已載入 {len(self.entries)} 個字幕條目，準備翻譯")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"載入SRT檔案失敗: {e}")
    
    def start_translation(self):
        if not self.batch_files:
            messagebox.showerror("錯誤", "請先選擇SRT檔案")
            return
        
        if not all([self.api_url_var.get(), self.model_var.get(), self.api_key_var.get()]):
            messagebox.showerror("錯誤", "請先配置API設定")
            return
        
        # 在新線程中執行批次翻譯
        threading.Thread(target=self.batch_translate_worker, daemon=True).start()
    
    def batch_translate_worker(self):
        try:
            self.translator = APITranslator(
                self.api_url_var.get(),
                self.model_var.get(),
                self.api_key_var.get()
            )
            
            total_files = len(self.batch_files)
            overall_stats = {'success': 0, 'failed': 0, 'total_entries': 0}
            
            for file_index, file_path in enumerate(self.batch_files):
                self.current_file_index = file_index
                filename = os.path.basename(file_path)
                
                self.progress_var.set(f"處理檔案 {file_index + 1}/{total_files}: {filename}")
                
                try:
                    # 載入SRT檔案
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    entries = SRTParser.parse_srt(content)
                    overall_stats['total_entries'] += len(entries)
                    
                    if not entries:
                        print(f"警告：檔案 {filename} 無法解析或為空")
                        continue
                    
                    # 翻譯檔案
                    file_stats = self.translate_single_file(entries, file_path, file_index, total_files)
                    overall_stats['success'] += file_stats['success']
                    overall_stats['failed'] += file_stats['failed']
                    
                except Exception as e:
                    print(f"處理檔案 {filename} 時發生錯誤: {e}")
                    continue
            
            # 顯示整體結果
            result_msg = f"批次翻譯完成！\n"
            result_msg += f"處理檔案數: {total_files}\n"
            result_msg += f"總條目數: {overall_stats['total_entries']}\n"
            result_msg += f"成功翻譯: {overall_stats['success']}\n"
            result_msg += f"翻譯失敗: {overall_stats['failed']}\n"
            result_msg += f"成功率: {overall_stats['success'] / max(1, overall_stats['total_entries']) * 100:.1f}%"
            
            self.progress_var.set(f"批次翻譯完成！成功 {overall_stats['success']}/{overall_stats['total_entries']}")
            messagebox.showinfo("完成", result_msg)
            
        except Exception as e:
            self.progress_var.set("批次翻譯失敗")
            messagebox.showerror("錯誤", f"批次翻譯失敗: {e}")
    
    def translate_single_file(self, entries, file_path, file_index, total_files):
        filename = os.path.basename(file_path)
        batch_translator = BatchTranslator(self.translator)
        batches = batch_translator.create_batches(entries, max_words=100)
        
        total_batches = len(batches)
        file_stats = {'success': 0, 'failed': 0}
        
        entry_idx = 0
        for batch_idx, batch in enumerate(batches):
            progress_text = f"檔案 {file_index + 1}/{total_files} ({filename}) - 翻譯批次 {batch_idx + 1}/{total_batches}"
            self.progress_var.set(progress_text)
            
            # 更新進度條
            overall_progress = ((file_index * 100) + (batch_idx + 1) * 100 / total_batches) / total_files
            self.progress_bar.config(maximum=100)
            self.progress_bar['value'] = overall_progress
            
            try:
                context = batch_translator.get_context(entries, entry_idx)
                translations = batch_translator.translate_batch(batch, context)
                
                for entry, translation in zip(batch, translations):
                    entry.translated_text = translation
                    if translation and not translation.startswith("[翻譯失敗]"):
                        file_stats['success'] += 1
                    else:
                        file_stats['failed'] += 1
                    entry_idx += 1
                    
            except Exception as e:
                print(f"檔案 {filename} 批次 {batch_idx + 1} 翻譯失敗: {e}")
                for entry in batch:
                    entry.translated_text = f"[翻譯失敗] {entry.text}"
                    file_stats['failed'] += 1
                    entry_idx += 1
            
            self.root.update_idletasks()
            time.sleep(1)  # API調用間隔
        
        # 保存翻譯結果
        base_name = os.path.splitext(file_path)[0]
        output_path = f"{base_name}.zh.srt"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(SRTParser.entries_to_srt(entries))
            print(f"檔案 {filename} 翻譯完成，輸出至: {output_path}")
        except Exception as e:
            print(f"保存檔案 {filename} 時發生錯誤: {e}")
        
        return file_stats
    
    def translate_worker(self):
        """Legacy method for single file translation"""
        try:
            self.translator = APITranslator(
                self.api_url_var.get(),
                self.model_var.get(),
                self.api_key_var.get()
            )
            
            batch_translator = BatchTranslator(self.translator)
            batches = batch_translator.create_batches(self.entries, max_words=100)
            
            self.progress_bar.config(maximum=len(batches))
            
            entry_idx = 0
            for batch_idx, batch in enumerate(batches):
                self.progress_var.set(f"翻譯中... ({batch_idx + 1}/{len(batches)})")
                
                context = batch_translator.get_context(self.entries, entry_idx)
                translations = batch_translator.translate_batch(batch, context)
                
                for entry, translation in zip(batch, translations):
                    entry.translated_text = translation
                    entry_idx += 1
                
                self.progress_bar['value'] = batch_idx + 1
                self.root.update_idletasks()
                time.sleep(1)
            
            untranslated_count = 0
            failed_entries = []
            
            for entry in self.entries:
                if not entry.translated_text or entry.translated_text.strip() == "":
                    untranslated_count += 1
                    failed_entries.append(entry.index)
                elif entry.translated_text.startswith("[翻譯失敗]"):
                    untranslated_count += 1
                    failed_entries.append(entry.index)
            
            base_name = os.path.splitext(self.file_path)[0]
            output_path = f"{base_name}.zh.srt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(SRTParser.entries_to_srt(self.entries))
            
            total_entries = len(self.entries)
            success_count = total_entries - untranslated_count
            
            result_msg = f"翻譯完成！\n"
            result_msg += f"總條目: {total_entries}\n"
            result_msg += f"成功翻譯: {success_count}\n"
            if untranslated_count > 0:
                result_msg += f"未翻譯/失敗: {untranslated_count}\n"
                result_msg += f"失敗條目: {failed_entries[:10]}{'...' if len(failed_entries) > 10 else ''}\n"
            result_msg += f"輸出檔案: {output_path}"
            
            self.progress_var.set(f"翻譯完成！成功 {success_count}/{total_entries}")
            messagebox.showinfo("完成", result_msg)
            
        except Exception as e:
            self.progress_var.set("翻譯失敗")
            messagebox.showerror("錯誤", f"翻譯失敗: {e}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SRTTranslatorGUI()
    app.run()