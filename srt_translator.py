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
    def __init__(self, api_url: str, model: str, api_key: str = ""):
        self.api_url = api_url
        self.model = model
        self.api_key = api_key.strip() if api_key else ""
        self.session = requests.Session()
        self.current_max_tokens = 1000  # 默認值
        
    def calculate_max_tokens(self, input_word_count: int) -> int:
        """根據輸入字數計算合適的max_tokens值"""
        # 基本公式：中文輸出通常比英文輸入短，但API需要額外空間
        # 估計每個英文詞對應1.2個中文字符，再加上一些緩衝
        estimated_output = int(input_word_count * 1.5)
        
        # 設定最小值和最大值
        min_tokens = 200
        max_tokens = 4000
        
        # 加上30%的緩衝空間
        calculated_tokens = int(estimated_output * 1.3)
        
        return max(min_tokens, min(calculated_tokens, max_tokens))
        
    def translate_text(self, text: str, context: str = "", word_count: int = None) -> str:
        prompt = f"""請將以下英文字幕翻譯成繁體中文。要求：
1. 保持原文的語氣和情感
2. 不要翻譯專有名詞（人名、地名、品牌名等）
3. 保持字幕的簡潔性
4. 確保翻譯自然流暢

{f"前面的上下文參考：{context}" if context else ""}

需要翻譯的文本：
{text}

只回覆翻譯結果，不要包含其他說明："""

        # 動態計算max_tokens
        if word_count:
            self.current_max_tokens = self.calculate_max_tokens(word_count)
        else:
            # 估算當前文本的詞數
            estimated_words = len(text.split())
            self.current_max_tokens = self.calculate_max_tokens(estimated_words)

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
            "Content-Type": "application/json"
        }
        
        # 只有当API key存在时才添加认证头
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": self.current_max_tokens
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
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # 只有当API key存在时才添加认证头
        if self.api_key:
            headers["x-api-key"] = self.api_key
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.current_max_tokens,
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
            "Content-Type": "application/json"
        }
        
        # 只有当API key存在时才添加认证头
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": self.current_max_tokens
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
        
        # 計算批次總字數
        total_words = sum(self.count_words(entry.text) for entry in batch)
        
        try:
            translated = self.translator.translate_text(batch_text, context, word_count=total_words)
            
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
        self.batch_files = []  # 存儲批次檔案列表，格式: [{'path': str, 'status': str, 'success': int, 'failed': int}]
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
        
        # 批次字數設定
        ttk.Label(config_frame, text="批次字數:").grid(row=3, column=0, sticky="w", pady=2)
        self.batch_words_var = tk.StringVar(value="100")
        batch_words_frame = ttk.Frame(config_frame)
        batch_words_frame.grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Entry(batch_words_frame, textvariable=self.batch_words_var, width=10).pack(side="left")
        ttk.Label(batch_words_frame, text="字 (建議: 50-200)").pack(side="left", padx=(5, 0))
        
        config_frame.columnconfigure(1, weight=1)
        
        # 按鈕框架
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(button_frame, text="保存配置", command=self.save_config).pack(side="left", padx=5)
        ttk.Button(button_frame, text="選擇檔案", command=self.select_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="刪除選中", command=self.remove_selected_file).pack(side="left", padx=5)
        ttk.Button(button_frame, text="清空檔案列表", command=self.clear_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="開始翻譯", command=self.start_translation).pack(side="left", padx=5)
        
        # 檔案列表框架
        files_frame = ttk.LabelFrame(self.root, text="待處理檔案列表", padding=10)
        files_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 檔案列表視窗（使用Treeview以顯示狀態）
        list_frame = ttk.Frame(files_frame)
        list_frame.pack(fill="both", expand=True)
        
        # 建立Treeview來顯示檔案和狀態
        columns = ('file', 'status', 'progress')
        self.files_tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
        
        # 設定欄位標題
        self.files_tree.heading('file', text='檔案名稱')
        self.files_tree.heading('status', text='狀態')
        self.files_tree.heading('progress', text='進度')
        
        # 設定欄位寬度
        self.files_tree.column('file', width=400)
        self.files_tree.column('status', width=100)
        self.files_tree.column('progress', width=150)
        
        # 滾動條
        tree_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.files_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")
        
        # 綁定右鍵選單
        self.files_tree.bind("<Button-3>", self.show_context_menu)
        
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
                    self.batch_words_var.set(config.get('batch_words', '100'))
            except Exception as e:
                print(f"載入配置失敗: {e}")
    
    def save_config(self):
        config = {
            'api_url': self.api_url_var.get(),
            'model': self.model_var.get(),
            'api_key': self.api_key_var.get(),
            'batch_words': self.batch_words_var.get()
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
        # 檢查檔案是否已存在
        for file_info in self.batch_files:
            if file_info['path'] == file_path:
                return
        
        # 嘗試解析SRT文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            entries = SRTParser.parse_srt(content)
        except Exception as e:
            messagebox.showerror("錯誤", f"無法解析SRT文件 {os.path.basename(file_path)}: {e}")
            return
        
        # 添加新檔案到列表
        file_info = {
            'path': file_path,
            'status': '未處理',
            'success': 0,
            'failed': 0,
            'entries': entries,
            'failed_indices': []
        }
        self.batch_files.append(file_info)
        
        # 在Treeview中添加項目
        filename = os.path.basename(file_path)
        entry_count = len(entries) if entries else 0
        self.files_tree.insert('', 'end', values=(filename, '未處理', f'0/{entry_count}'))
        
        self.update_status_display()
    
    def clear_files(self):
        self.batch_files.clear()
        self.files_tree.delete(*self.files_tree.get_children())
        self.update_status_display()
    
    def remove_selected_file(self):
        selected_item = self.files_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "請選擇要刪除的檔案")
            return
        
        # 取得選中的項目索引
        item_index = self.files_tree.index(selected_item[0])
        
        # 從檔案列表中刪除
        if 0 <= item_index < len(self.batch_files):
            removed_file = self.batch_files.pop(item_index)
            filename = os.path.basename(removed_file['path'])
            
            # 從Treeview中刪除
            self.files_tree.delete(selected_item[0])
            
            # 更新狀態顯示
            self.update_status_display()
            
            messagebox.showinfo("成功", f"已刪除檔案: {filename}")
    
    def show_context_menu(self, event):
        """顯示右鍵選單"""
        # 選中被右鍵點擊的項目
        item = self.files_tree.identify_row(event.y)
        if not item:
            return
        
        self.files_tree.selection_set(item)
        
        # 獲取檔案信息
        item_index = self.files_tree.index(item)
        if item_index >= len(self.batch_files):
            return
        
        file_info = self.batch_files[item_index]
        
        # 創建右鍵選單
        context_menu = tk.Menu(self.root, tearoff=0)
        
        # 根據檔案狀態動態添加選項
        if file_info['status'] in ['部分失敗'] and file_info['failed_indices']:
            context_menu.add_command(label="重試失敗項目", command=lambda: self.retry_failed_entries(item_index))
        
        if file_info['status'] in ['完成', '部分失敗', '失敗']:
            context_menu.add_command(label="重新翻譯整個文件", command=lambda: self.retranslate_file(item_index))
        
        if file_info['status'] == '完成' or (file_info['status'] == '部分失敗' and file_info['success'] > 0):
            context_menu.add_command(label="打開翻譯結果", command=lambda: self.open_translated_file(item_index))
        
        context_menu.add_separator()
        context_menu.add_command(label="打開文件位置", command=lambda: self.open_file_location(item_index))
        context_menu.add_command(label="從列表中移除", command=lambda: self.remove_file_by_index(item_index))
        
        # 顯示選單
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def update_status_display(self):
        count = len(self.batch_files)
        if count == 0:
            self.drag_label.config(text="將SRT檔案拖拽到此處\n或點擊上方按鈕選擇檔案\n支援批次處理")
            self.progress_var.set("準備就緒")
        else:
            # 統計狀態
            pending_count = sum(1 for f in self.batch_files if f['status'] == '未處理')
            processing_count = sum(1 for f in self.batch_files if f['status'] == '處理中')
            completed_count = sum(1 for f in self.batch_files if f['status'] == '完成')
            failed_count = sum(1 for f in self.batch_files if f['status'] in ['失敗', '部分失敗'])
            
            status_text = f"已選擇 {count} 個檔案\n"
            if pending_count > 0:
                status_text += f"未處理: {pending_count} "
            if processing_count > 0:
                status_text += f"處理中: {processing_count} "
            if completed_count > 0:
                status_text += f"完成: {completed_count} "
            if failed_count > 0:
                status_text += f"失敗: {failed_count}"
            
            self.drag_label.config(text=status_text.strip())
            
            if processing_count > 0:
                self.progress_var.set(f"正在處理檔案... (完成: {completed_count}, 失敗: {failed_count})")
            else:
                self.progress_var.set(f"已選擇 {count} 個檔案，準備翻譯")
    
    def update_file_display(self, file_index, filename, status, progress):
        """更新Treeview中特定檔案的顯示"""
        try:
            # 取得所有children
            children = self.files_tree.get_children()
            if 0 <= file_index < len(children):
                item_id = children[file_index]
                self.files_tree.item(item_id, values=(filename, status, progress))
        except Exception as e:
            print(f"更新檔案顯示失敗: {e}")
    
    def retry_failed_entries(self, file_index):
        """重試失敗的條目"""
        if file_index >= len(self.batch_files):
            return
        
        file_info = self.batch_files[file_index]
        if not file_info['failed_indices']:
            messagebox.showinfo("提示", "沒有失敗的條目需要重試")
            return
        
        # 檢查API配置
        if not self.api_url_var.get().strip() or not self.model_var.get().strip():
            messagebox.showerror("錯誤", "請先配置API網址和模型")
            return
        
        # 在新線程中執行重試
        threading.Thread(target=self.retry_failed_worker, args=(file_index,), daemon=True).start()
    
    def retry_failed_worker(self, file_index):
        """重試失敗條目的工作線程"""
        try:
            # 初始化translator
            if not self.translator:
                self.translator = APITranslator(
                    self.api_url_var.get(),
                    self.model_var.get(),
                    self.api_key_var.get()
                )
            
            file_info = self.batch_files[file_index]
            filename = os.path.basename(file_info['path'])
            failed_indices = file_info['failed_indices'].copy()
            
            self.progress_var.set(f"重試失敗條目: {filename}")
        except Exception as e:
            self.progress_var.set("重試失敗")
            messagebox.showerror("錯誤", f"初始化API失敗: {e}")
            return
        
        retry_success = 0
        retry_failed = 0
        new_failed_indices = []
        
        for idx in failed_indices:
            if idx < len(file_info['entries']):
                entry = file_info['entries'][idx]
                try:
                    # 單獨翻譯失敗的條目
                    translation = self.translator.translate_text(entry.text)
                    entry.translated_text = translation.strip()
                    
                    if translation and not translation.startswith("[翻譯失敗]"):
                        retry_success += 1
                    else:
                        retry_failed += 1
                        new_failed_indices.append(idx)
                        
                except Exception as e:
                    print(f"重試條目 {idx} 失敗: {e}")
                    entry.translated_text = f"[翻譯失敗] {entry.text}"
                    retry_failed += 1
                    new_failed_indices.append(idx)
        
        # 更新統計
        file_info['success'] += retry_success
        file_info['failed'] -= retry_success
        file_info['failed_indices'] = new_failed_indices
        
        # 更新狀態
        if not new_failed_indices:
            file_info['status'] = '完成'
            status_text = '完成'
        else:
            status_text = '部分失敗'
        
        total_entries = len(file_info['entries'])
        progress_text = f"{file_info['success']}/{total_entries}"
        self.update_file_display(file_index, filename, status_text, progress_text)
        self.update_status_display()
        
        # 保存結果
        try:
            base_name = os.path.splitext(file_info['path'])[0]
            output_path = f"{base_name}.zh.srt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(SRTParser.entries_to_srt(file_info['entries']))
        except Exception as e:
            print(f"保存重試結果失敗: {e}")
        
        self.progress_var.set(f"重試完成: 成功 {retry_success}, 失敗 {retry_failed}")
    
    def retranslate_file(self, file_index):
        """重新翻譯整個文件"""
        if file_index >= len(self.batch_files):
            return
        
        file_info = self.batch_files[file_index]
        filename = os.path.basename(file_info['path'])
        
        if messagebox.askyesno("確認", f"確定要重新翻譯整個文件 {filename} 嗎？\n這將覆蓋現有的翻譯結果。"):
            # 重置文件狀態
            file_info['status'] = '未處理'
            file_info['success'] = 0
            file_info['failed'] = 0
            file_info['failed_indices'] = []
            
            # 清除現有翻譯
            for entry in file_info['entries']:
                entry.translated_text = ""
            
            # 更新顯示
            total_entries = len(file_info['entries'])
            self.update_file_display(file_index, filename, '未處理', f'0/{total_entries}')
            self.update_status_display()
    
    def open_translated_file(self, file_index):
        """打開翻譯結果文件"""
        if file_index >= len(self.batch_files):
            return
        
        file_info = self.batch_files[file_index]
        base_name = os.path.splitext(file_info['path'])[0]
        translated_path = f"{base_name}.zh.srt"
        
        if os.path.exists(translated_path):
            try:
                import subprocess
                subprocess.run(['start', translated_path], shell=True)
            except Exception as e:
                messagebox.showerror("錯誤", f"無法打開文件: {e}")
        else:
            messagebox.showwarning("警告", "翻譯結果文件不存在")
    
    def open_file_location(self, file_index):
        """打開文件所在位置"""
        if file_index >= len(self.batch_files):
            return
        
        file_info = self.batch_files[file_index]
        file_dir = os.path.dirname(file_info['path'])
        
        try:
            import subprocess
            subprocess.run(['explorer', file_dir], shell=True)
        except Exception as e:
            messagebox.showerror("錯誤", f"無法打開文件位置: {e}")
    
    def remove_file_by_index(self, file_index):
        """通過索引刪除文件"""
        if file_index >= len(self.batch_files):
            return
        
        file_info = self.batch_files[file_index]
        filename = os.path.basename(file_info['path'])
        
        # 從列表中刪除
        self.batch_files.pop(file_index)
        
        # 從Treeview中刪除
        children = self.files_tree.get_children()
        if file_index < len(children):
            self.files_tree.delete(children[file_index])
        
        # 更新狀態顯示
        self.update_status_display()
    
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
        
        # 检查必要的配置（API key对于本地服务如ollama是可选的）
        if not self.api_url_var.get().strip() or not self.model_var.get().strip():
            messagebox.showerror("錯誤", "請先配置API網址和模型")
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
            
            for file_index, file_info in enumerate(self.batch_files):
                self.current_file_index = file_index
                file_path = file_info['path']
                filename = os.path.basename(file_path)
                
                # 更新檔案狀態為處理中
                file_info['status'] = '處理中'
                self.update_file_display(file_index, filename, '處理中', '0/0')
                
                self.progress_var.set(f"處理檔案 {file_index + 1}/{total_files}: {filename}")
                
                try:
                    # 使用已解析的條目
                    entries = file_info['entries']
                    overall_stats['total_entries'] += len(entries)
                    
                    if not entries:
                        print(f"警告：檔案 {filename} 無法解析或為空")
                        file_info['status'] = '失敗'
                        self.update_file_display(file_index, filename, '失敗', '0/0')
                        continue
                    
                    # 翻譯檔案
                    file_stats = self.translate_single_file(file_info, file_index, total_files)
                    file_info['success'] = file_stats['success']
                    file_info['failed'] = file_stats['failed']
                    file_info['failed_indices'] = file_stats['failed_indices']
                    
                    overall_stats['success'] += file_stats['success']
                    overall_stats['failed'] += file_stats['failed']
                    
                    # 更新最終狀態
                    if file_stats['failed'] == 0:
                        file_info['status'] = '完成'
                        status_text = '完成'
                    else:
                        file_info['status'] = '部分失敗'
                        status_text = '部分失敗'
                    
                    progress_text = f"{file_stats['success']}/{file_stats['success'] + file_stats['failed']}"
                    self.update_file_display(file_index, filename, status_text, progress_text)
                    self.update_status_display()  # 更新主要狀態顯示
                    
                except Exception as e:
                    print(f"處理檔案 {filename} 時發生錯誤: {e}")
                    file_info['status'] = '失敗'
                    self.update_file_display(file_index, filename, '失敗', '0/0')
                    self.update_status_display()  # 更新主要狀態顯示
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
    
    def translate_single_file(self, file_info, file_index, total_files):
        file_path = file_info['path']
        entries = file_info['entries']
        filename = os.path.basename(file_path)
        batch_translator = BatchTranslator(self.translator)
        # 獲取批次字數設定
        try:
            max_words = int(self.batch_words_var.get())
            if max_words < 10:
                max_words = 10
            elif max_words > 500:
                max_words = 500
        except ValueError:
            max_words = 100
        
        batches = batch_translator.create_batches(entries, max_words=max_words)
        
        total_batches = len(batches)
        file_stats = {'success': 0, 'failed': 0, 'failed_indices': []}
        
        entry_idx = 0
        for batch_idx, batch in enumerate(batches):
            progress_text = f"檔案 {file_index + 1}/{total_files} ({filename}) - 翻譯批次 {batch_idx + 1}/{total_batches}"
            self.progress_var.set(progress_text)
            
            # 更新進度條
            overall_progress = ((file_index * 100) + (batch_idx + 1) * 100 / total_batches) / total_files
            self.progress_bar.config(maximum=100)
            self.progress_bar['value'] = overall_progress
            
            # 更新檔案進度顯示
            current_progress = f"{file_stats['success'] + file_stats['failed']}/{len(entries)}"
            self.update_file_display(file_index, filename, '處理中', current_progress)
            
            try:
                context = batch_translator.get_context(entries, entry_idx)
                translations = batch_translator.translate_batch(batch, context)
                
                for entry, translation in zip(batch, translations):
                    entry.translated_text = translation
                    if translation and not translation.startswith("[翻譯失敗]"):
                        file_stats['success'] += 1
                    else:
                        file_stats['failed'] += 1
                        file_stats['failed_indices'].append(entry_idx)
                    entry_idx += 1
                    
            except Exception as e:
                print(f"檔案 {filename} 批次 {batch_idx + 1} 翻譯失敗: {e}")
                for entry in batch:
                    entry.translated_text = f"[翻譯失敗] {entry.text}"
                    file_stats['failed'] += 1
                    file_stats['failed_indices'].append(entry_idx)
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
            # 獲取批次字數設定
            try:
                max_words = int(self.batch_words_var.get())
                if max_words < 10:
                    max_words = 10
                elif max_words > 500:
                    max_words = 500
            except ValueError:
                max_words = 100
            
            batches = batch_translator.create_batches(self.entries, max_words=max_words)
            
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