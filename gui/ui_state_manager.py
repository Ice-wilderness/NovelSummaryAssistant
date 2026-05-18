# python/gui/ui_state_manager.py

import customtkinter as ctk
import os
import yaml

class UiStateManagerMixin:
    """
    一个 Mixin 类，用于集中管理 UI 控件在不同状态下的启用/禁用。
    """
    def _get_all_children(self, parent):
        """递归地获取一个控件下的所有后代控件。"""
        for child in parent.winfo_children():
            yield child
            yield from self._get_all_children(child)

    def __init__(self):
        # 此 Mixin 不需要独立的状态，其方法直接操作 self (主GUI实例) 上的控件
        # --- 路径现在由主程序(main_app.py)在启动时统一设置 ---
        # --- 并赋值给 self.config_path 和 self.api_config_path ---
        pass

    def load_initial_ui_state(self):
        """
        加载或设置UI的初始状态。
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data:
                # 恢复各种路径和设置
                if hasattr(self, 'novel_folder_path'): self.novel_folder_path.set(data.get('novel_folder_path', ''))
                if hasattr(self, 'splitter_output_dir_path_var'): self.splitter_output_dir_path_var.set(data.get('splitter_output_dir', ''))
                if hasattr(self, 'source_txt_file_path_var'): self.source_txt_file_path_var.set(data.get('source_txt_file', ''))
                if hasattr(self, 'splitter_mode_var'): self.splitter_mode_var.set(data.get('splitter_mode', 'default'))
                if hasattr(self, 'regex_pattern_var'): self.regex_pattern_var.set(data.get('regex_pattern', ''))
                if hasattr(self, 'chapters_per_file_var'): self.chapters_per_file_var.set(data.get('chapters_per_file', 1))
                if hasattr(self, 'handle_volumes_var'): self.handle_volumes_var.set(data.get('handle_volumes', True))
                if hasattr(self, 'summary_mode_var'): self.summary_mode_var.set(data.get('summary_mode', 'novel'))
                if hasattr(self, 'big_summary_batch_size_var'): self.big_summary_batch_size_var.set(data.get('big_summary_batch_size', '5'))
                if hasattr(self, 'ultimate_api_selector_var'): self.ultimate_api_selector_var.set(data.get('ultimate_api_id', '默认 (第一个API)'))
                
                # --- 新增：加载大总结精细控制流程的设置 ---
                if hasattr(self, 'use_fine_grained_flow_var'): self.use_fine_grained_flow_var.set(data.get('use_fine_grained_flow', False))
                if hasattr(self, 'super_summary_threshold_var'): self.super_summary_threshold_var.set(data.get('super_summary_threshold', '5'))
                if hasattr(self, 'super_summary_api_assignments'): self.super_summary_api_assignments = data.get('super_summary_api_assignments', {})
                
                # 恢复字数设置
                if 'word_counts' in data and hasattr(self, 'word_count_vars'):
                    for key, value in data['word_counts'].items():
                        if key in self.word_count_vars:
                            self.word_count_vars[key].set(value)
        except (FileNotFoundError, IOError, yaml.YAMLError) as e:
            self.log_message_gui("global", f"加载UI配置文件 '{self.config_path}' 失败，将使用默认设置。错误: {e}")

        self.load_api_configs_from_file() # 加载API配置
        self.set_ui_state_idle()

    def set_ui_state_running(self):
        """将UI设置为"任务运行中"状态。"""
        # --- 主控制按钮 ---
        self.button_start.configure(state="disabled")
        self.button_pause.configure(state="normal", text="暂停")
        self.button_stop.configure(state="normal")
        self.button_reset_cache.configure(state="disabled")
        
        # --- 精细化锁定：只锁定与主总结任务强相关的选项卡 ---

        # 1. 锁定"主总结任务"选项卡内的所有交互组件
        # 假设这些组件都在 self.main_task_frame 中
        if hasattr(self, 'tab_main'):
            for widget in self._get_all_children(self.tab_main):
                if isinstance(widget, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkComboBox, ctk.CTkRadioButton, ctk.CTkCheckBox, ctk.CTkSwitch)):
                    widget.configure(state="disabled")

        # 2. 锁定"API 配置"选项卡
        self.batch_size_entry.configure(state="disabled")
        if hasattr(self, 'add_api_button'): self.add_api_button.configure(state="disabled")
        if hasattr(self, 'save_api_button'): self.save_api_button.configure(state="disabled")
        if hasattr(self, 'load_api_button'): self.load_api_button.configure(state="disabled")
        if hasattr(self, 'button_reset_api'): self.button_reset_api.configure(state="disabled")
        for api_entry in getattr(self, 'api_entries', []):
            api_entry['frame'].configure(fg_color=("gray85", "gray20")) # 变灰提示
            for widget in api_entry.values():
                if isinstance(widget, (ctk.CTkEntry, ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkComboBox)):
                    widget.configure(state="disabled")

        # 3. 锁定"提示词编辑器"选项卡
        self.button_reset_prompt.configure(state="disabled")
        self.button_save_prompt.configure(state="disabled")
        self.prompt_combobox.configure(state="disabled")
        self.prompt_text_area.configure(state="disabled")

        # 4. 解锁（或保持解锁）其他功能
        # "自定义总结" 和 "章节分割工具" 选项卡下的控件不受影响。
        # self.notebook (主选项卡控件) 也可以切换。

    def set_ui_state_paused(self):
        """将UI设置为"任务暂停中"状态。"""
        # --- 主控制按钮 ---
        self.button_start.configure(state="disabled")
        self.button_pause.configure(state="normal", text="继续")
        self.button_stop.configure(state="normal")
        self.button_reset_cache.configure(state="disabled") # 暂停时也不应重置缓存
        
        # --- API 配置页 (在暂停时允许修改，但只对下次任务生效) ---
        # 解释：允许在暂停时编辑API配置，但这些更改不会影响当前正在运行的任务。
        # 更改将在下一次点击"开始"时生效。
        self.batch_size_entry.configure(state="normal")
        if hasattr(self, 'add_api_button'): self.add_api_button.configure(state="normal")
        if hasattr(self, 'save_api_button'): self.save_api_button.configure(state="normal")
        if hasattr(self, 'load_api_button'): self.load_api_button.configure(state="normal")
        if hasattr(self, 'button_reset_api'): self.button_reset_api.configure(state="normal")
        for api_entry in getattr(self, 'api_entries', []):
            api_entry['frame'].configure(fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"]) # 恢复颜色
            for widget in api_entry.values():
                if isinstance(widget, (ctk.CTkEntry, ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkComboBox)):
                    widget.configure(state="normal")
        
        # --- 提示词编辑页 (在暂停时应可编辑) ---
        self.button_reset_prompt.configure(state="normal")
        self.button_save_prompt.configure(state="normal") # 允许保存
        self.prompt_combobox.configure(state="readonly") # 允许切换
        self.prompt_text_area.configure(state="normal") # 允许编辑


    def set_ui_state_idle(self):
        """将UI设置为"空闲"状态。"""
        # 将每个主要UI区域的重置操作包裹在独立的try-except块中，以增加健壮性。
        # 即使某个区域的UI组件不存在或更新失败，也不会影响其他区域的状态重置。
        
        # --- 主控制按钮 ---
        try:
            self.button_start.configure(state="normal")
            self.button_pause.configure(state="disabled", text="暂停")
            self.button_stop.configure(state="disabled")
            self.button_reset_cache.configure(state="normal")
        except Exception as e:
            print(f"Error resetting main controls state: {e}")

        # --- API 配置页 ---
        try:
            if hasattr(self, 'batch_size_entry'): self.batch_size_entry.configure(state="normal")
            if hasattr(self, 'add_api_button'): self.add_api_button.configure(state="normal")
            if hasattr(self, 'save_api_button'): self.save_api_button.configure(state="normal")
            if hasattr(self, 'load_api_button'): self.load_api_button.configure(state="normal")
            if hasattr(self, 'button_reset_api'): self.button_reset_api.configure(state="normal")
            
            # 启用滚动列表内的所有条目控件
            for api_entry in getattr(self, 'api_entries', []):
                if 'frame' in api_entry and api_entry['frame'].winfo_exists():
                    api_entry['frame'].configure(fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
                for widget_key, widget in api_entry.items():
                    if isinstance(widget, (ctk.CTkEntry, ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkComboBox)):
                        if widget.winfo_exists():
                            widget.configure(state="normal")
        except Exception as e:
            print(f"Error resetting API config tab state: {e}")


        # --- 提示词编辑页 ---
        try:
            if hasattr(self, 'button_reset_prompt'): self.button_reset_prompt.configure(state="normal")
            if hasattr(self, 'button_save_prompt'): self.button_save_prompt.configure(state="normal")
            if hasattr(self, 'prompt_combobox'): self.prompt_combobox.configure(state="readonly")
            if hasattr(self, 'prompt_text_area'): self.prompt_text_area.configure(state="normal")
        except Exception as e:
            print(f"Error resetting prompt editor tab state: {e}")

        # --- 解锁所有选项卡 ---
        try:
            for tab in [self.tab_main, self.tab_api_config, self.tab_prompts, self.tab_custom_summary, self.tab_splitter]:
                 for widget in self._get_all_children(tab):
                    if isinstance(widget, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkComboBox, ctk.CTkRadioButton, ctk.CTkCheckBox, ctk.CTkSwitch)):
                        if isinstance(widget, ctk.CTkComboBox) and tab == self.tab_prompts:
                             widget.configure(state="readonly")
                        else:
                            widget.configure(state="normal")
        except Exception as e:
            print(f"Error resetting tabs state: {e}")

    def save_ui_state(self):
        """
        将当前UI的重要状态保存到 config.yaml 文件。
        此方法在窗口关闭时调用。
        """
        state = {
            'novel_folder_path': self.novel_folder_path.get() if hasattr(self, 'novel_folder_path') else '',
            'splitter_output_dir': self.splitter_output_dir_path_var.get() if hasattr(self, 'splitter_output_dir_path_var') else '',
            'source_txt_file': self.source_txt_file_path_var.get() if hasattr(self, 'source_txt_file_path_var') else '',
            'splitter_mode': self.splitter_mode_var.get() if hasattr(self, 'splitter_mode_var') else 'default',
            'regex_pattern': self.regex_pattern_var.get() if hasattr(self, 'regex_pattern_var') else '',
            'chapters_per_file': self.chapters_per_file_var.get() if hasattr(self, 'chapters_per_file_var') else 1,
            'handle_volumes': self.handle_volumes_var.get() if hasattr(self, 'handle_volumes_var') else True,
            'summary_mode': self.summary_mode_var.get() if hasattr(self, 'summary_mode_var') else 'novel',
            'big_summary_batch_size': self.big_summary_batch_size_var.get() if hasattr(self, 'big_summary_batch_size_var') else '5',
            'ultimate_api_id': self.ultimate_api_selector_var.get() if hasattr(self, 'ultimate_api_selector_var') else '默认 (第一个API)',
            'window_geometry': self.root.geometry(),
            'word_counts': {key: var.get() for key, var in self.word_count_vars.items()} if hasattr(self, 'word_count_vars') else {},
            # --- 新增：保存大总结精细控制流程的设置 ---
            'use_fine_grained_flow': self.use_fine_grained_flow_var.get() if hasattr(self, 'use_fine_grained_flow_var') else False,
            'super_summary_threshold': self.super_summary_threshold_var.get() if hasattr(self, 'super_summary_threshold_var') else '5',
            'super_summary_api_assignments': self.super_summary_api_assignments if hasattr(self, 'super_summary_api_assignments') else {},
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(state, f, allow_unicode=True, sort_keys=False)
            # 保存成功时不再需要记录日志或做任何多余操作
        except Exception as e:
            # 只在控制台打印错误，避免在关闭过程中弹窗或卡住
            print(f"ERROR: 保存UI状态到 '{self.config_path}' 时出错: {e}")

    def load_api_configs_from_file(self):
        # 此方法现在由 ApiManagerMixin 提供，这里留空或移除
        # 父类中的实现将被使用
        super().load_api_configs_from_file()
