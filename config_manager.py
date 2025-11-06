"""
配置管理模块
负责 Bitget 跟单配置的加载、保存和更新
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "bitget_config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # 默认配置
        self.default_config = {
            "enabled": False,  # 是否启用自动跟单
            "scale_ratio": 0.1,  # 缩放比例（默认 10%）
            "whitelist_models": [],  # 白名单模型列表
            "max_single_trade_amount": 1000,  # 单笔交易最大金额（USDT）
            "api_credentials_from_env": True,  # API 密钥从环境变量读取
            "notification_on_trade": True,  # 交易执行后发送通知
            "dry_run": False  # 模拟运行模式（不实际下单）
        }
        
        # 确保配置文件存在
        self._ensure_config_file()
    
    def _ensure_config_file(self):
        """确保配置文件存在，不存在则创建默认配置"""
        if not os.path.exists(self.config_file):
            self.logger.info(f"配置文件不存在，创建默认配置: {self.config_file}")
            self.save_config(self.default_config)
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置
        
        Returns:
            配置字典
        """
        try:
            if not os.path.exists(self.config_file):
                self.logger.warning(f"配置文件不存在: {self.config_file}，使用默认配置")
                return self.default_config.copy()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 合并默认配置（确保所有字段都存在）
            merged_config = self.default_config.copy()
            merged_config.update(config)
            
            self.logger.info(f"配置加载成功: {self.config_file}")
            return merged_config
            
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {e}，使用默认配置")
            return self.default_config.copy()
        except Exception as e:
            self.logger.error(f"加载配置时发生错误: {e}，使用默认配置")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置
        
        Args:
            config: 配置字典
            
        Returns:
            成功返回 True，失败返回 False
        """
        try:
            # 验证配置
            validated_config = self._validate_config(config)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(validated_config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"配置保存成功: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置时发生错误: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        更新配置（部分更新）
        
        Args:
            updates: 要更新的配置项
            
        Returns:
            成功返回 True，失败返回 False
        """
        try:
            # 加载当前配置
            config = self.load_config()
            
            # 更新配置
            config.update(updates)
            
            # 保存配置
            return self.save_config(config)
            
        except Exception as e:
            self.logger.error(f"更新配置时发生错误: {e}")
            return False
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并规范化配置
        
        Args:
            config: 待验证的配置
            
        Returns:
            验证后的配置
        """
        validated = self.default_config.copy()
        
        # 验证并设置 enabled
        if 'enabled' in config:
            validated['enabled'] = bool(config['enabled'])
        
        # 验证并设置 scale_ratio
        if 'scale_ratio' in config:
            try:
                ratio = float(config['scale_ratio'])
                if 0 < ratio <= 1:
                    validated['scale_ratio'] = ratio
                else:
                    self.logger.warning(f"缩放比例超出范围 (0, 1]: {ratio}，使用默认值 0.1")
                    validated['scale_ratio'] = 0.1
            except (ValueError, TypeError):
                self.logger.warning(f"缩放比例格式错误: {config['scale_ratio']}，使用默认值 0.1")
                validated['scale_ratio'] = 0.1
        
        # 验证并设置 whitelist_models
        if 'whitelist_models' in config:
            if isinstance(config['whitelist_models'], list):
                validated['whitelist_models'] = [str(m) for m in config['whitelist_models']]
            else:
                self.logger.warning(f"白名单模型格式错误，应为列表: {config['whitelist_models']}")
                validated['whitelist_models'] = []
        
        # 验证并设置 max_single_trade_amount
        if 'max_single_trade_amount' in config:
            try:
                amount = float(config['max_single_trade_amount'])
                if amount > 0:
                    validated['max_single_trade_amount'] = amount
                else:
                    self.logger.warning(f"单笔交易最大金额必须大于 0: {amount}，使用默认值 1000")
                    validated['max_single_trade_amount'] = 1000
            except (ValueError, TypeError):
                self.logger.warning(f"单笔交易最大金额格式错误: {config['max_single_trade_amount']}，使用默认值 1000")
                validated['max_single_trade_amount'] = 1000
        
        # 验证并设置其他布尔值
        for key in ['api_credentials_from_env', 'notification_on_trade', 'dry_run']:
            if key in config:
                validated[key] = bool(config[key])
        
        return validated
    
    def get_enabled(self) -> bool:
        """获取是否启用自动跟单"""
        config = self.load_config()
        return config.get('enabled', False)
    
    def set_enabled(self, enabled: bool) -> bool:
        """设置是否启用自动跟单"""
        return self.update_config({'enabled': enabled})
    
    def get_scale_ratio(self) -> float:
        """获取缩放比例"""
        config = self.load_config()
        return config.get('scale_ratio', 0.1)
    
    def set_scale_ratio(self, ratio: float) -> bool:
        """设置缩放比例"""
        return self.update_config({'scale_ratio': ratio})
    
    def get_whitelist_models(self) -> List[str]:
        """获取白名单模型列表"""
        config = self.load_config()
        return config.get('whitelist_models', [])
    
    def set_whitelist_models(self, models: List[str]) -> bool:
        """设置白名单模型列表"""
        return self.update_config({'whitelist_models': models})
    
    def is_model_whitelisted(self, model_id: str) -> bool:
        """
        检查模型是否在白名单中
        
        Args:
            model_id: 模型ID
            
        Returns:
            如果白名单为空（跟随所有模型）或模型在白名单中，返回 True
        """
        whitelist = self.get_whitelist_models()
        
        # 白名单为空表示跟随所有模型
        if not whitelist:
            return True
        
        return model_id in whitelist
    
    def get_max_single_trade_amount(self) -> float:
        """获取单笔交易最大金额"""
        config = self.load_config()
        return config.get('max_single_trade_amount', 1000)
    
    def is_dry_run(self) -> bool:
        """获取是否为模拟运行模式"""
        config = self.load_config()
        return config.get('dry_run', False)


