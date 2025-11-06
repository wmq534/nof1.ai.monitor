#!/usr/bin/env python3
"""
跟单管理模块
支持多个交易平台的自动跟单功能
"""
import logging
from typing import List, Dict, Optional, Protocol
from datetime import datetime
from abc import ABC, abstractmethod


class TradeExecutor(Protocol):
    """
    交易执行器协议（接口）
    所有交易平台需要实现此接口
    """
    
    @property
    def scale_ratio(self) -> float:
        """获取缩放比例"""
        ...
    
    @scale_ratio.setter
    def scale_ratio(self, value: float):
        """设置缩放比例"""
        ...
    
    def execute_trades(self, trades: List[Dict]) -> Dict:
        """
        执行交易列表
        
        Args:
            trades: 交易列表
            
        Returns:
            {'success': int, 'failed': int, 'details': List[Dict]}
        """
        ...
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        ...


class FollowTradeManager:
    """
    跟单管理器
    管理多个交易平台的自动跟单功能
    """
    
    def __init__(self, config_manager=None):
        """
        初始化跟单管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        # 存储已注册的交易平台
        # 格式: {'platform_name': {'executor': TradeExecutor, 'enabled': bool}}
        self.platforms: Dict[str, Dict] = {}
        
        # 通知器
        self.notifiers = {
            'wechat': None,
            'telegram': None
        }
        
        self.logger.info("跟单管理器初始化完成")
    
    def register_platform(self, platform_name: str, executor: TradeExecutor, 
                         enabled: bool = True) -> None:
        """
        注册交易平台
        
        Args:
            platform_name: 平台名称（如 'bitget', 'binance'）
            executor: 交易执行器实例
            enabled: 是否启用该平台的跟单
        """
        self.platforms[platform_name] = {
            'executor': executor,
            'enabled': enabled
        }
        self.logger.info(f"✅ 注册交易平台: {platform_name} (启用: {enabled})")
    
    def unregister_platform(self, platform_name: str) -> None:
        """
        取消注册交易平台
        
        Args:
            platform_name: 平台名称
        """
        if platform_name in self.platforms:
            del self.platforms[platform_name]
            self.logger.info(f"❌ 取消注册交易平台: {platform_name}")
    
    def set_platform_enabled(self, platform_name: str, enabled: bool) -> None:
        """
        设置平台是否启用
        
        Args:
            platform_name: 平台名称
            enabled: 是否启用
        """
        if platform_name in self.platforms:
            self.platforms[platform_name]['enabled'] = enabled
            self.logger.info(f"设置平台 {platform_name} 启用状态: {enabled}")
    
    def register_notifier(self, notifier_type: str, notifier) -> None:
        """
        注册通知器
        
        Args:
            notifier_type: 通知类型 ('wechat', 'telegram')
            notifier: 通知器实例
        """
        if notifier_type in self.notifiers:
            self.notifiers[notifier_type] = notifier
            self.logger.info(f"✅ 注册通知器: {notifier_type}")
    
    def execute_follow_trades(self, trades: List[Dict]) -> Dict[str, Dict]:
        """
        执行跟单（所有启用的平台）
        
        Args:
            trades: 交易变化列表
            
        Returns:
            {'platform_name': {'success': int, 'failed': int, 'details': []}, ...}
        """
        results = {}
        
        try:
            self.logger.info(f"")
            self.logger.info(f"{'='*80}")
            self.logger.info(f"🤖 开始执行跟单流程")
            self.logger.info(f"   接收到的交易数量: {len(trades)}")
            self.logger.info(f"{'='*80}")
            
            # 检查是否有启用的平台
            self.logger.info(f"📋 检查已注册的平台...")
            self.logger.info(f"   已注册平台: {list(self.platforms.keys())}")
            
            enabled_platforms = {name: info for name, info in self.platforms.items() 
                               if info['enabled']}
            
            self.logger.info(f"   启用的平台: {list(enabled_platforms.keys())}")
            
            if not enabled_platforms:
                self.logger.warning("❌ 没有启用的交易平台，跳过跟单")
                return results
            
            # 检查是否启用自动跟单（通过配置管理器）
            if self.config_manager:
                auto_follow_enabled = self.config_manager.get_enabled()
                self.logger.info(f"⚙️  自动跟单配置状态: {'启用' if auto_follow_enabled else '禁用'}")
                
                if not auto_follow_enabled:
                    self.logger.warning("❌ 自动跟单功能未启用（配置文件中disabled），跳过")
                    return results
            else:
                self.logger.warning("⚠️  没有配置管理器，无法检查自动跟单状态")
            
            # 检查是否为模拟运行模式
            is_dry_run = False
            if self.config_manager:
                is_dry_run = self.config_manager.is_dry_run()
                self.logger.info(f"🎭 运行模式: {'模拟运行（只记录日志）' if is_dry_run else '实盘运行（实际下单）'}")
                if is_dry_run:
                    self.logger.info("🔸 模拟运行模式：只记录日志，不实际下单")
            
            # 过滤白名单模型
            self.logger.info(f"")
            self.logger.info(f"🔍 开始过滤白名单模型...")
            filtered_trades = self._filter_whitelist_trades(trades)
            
            whitelist = self.config_manager.get_whitelist_models() if self.config_manager else []
            self.logger.info(f"   白名单配置: {whitelist if whitelist else '全部模型'}")
            self.logger.info(f"   过滤前交易数: {len(trades)}")
            self.logger.info(f"   过滤后交易数: {len(filtered_trades)}")
            
            if not filtered_trades:
                self.logger.warning("❌ 没有符合白名单条件的交易，跳过跟单")
                return results
            
            self.logger.info(f"")
            self.logger.info(f"✅ 准备在 {len(enabled_platforms)} 个平台执行 {len(filtered_trades)} 个跟单交易")
            self.logger.info(f"{'='*80}")
            
            # 在每个启用的平台上执行跟单
            for platform_name, platform_info in enabled_platforms.items():
                executor = platform_info['executor']
                
                try:
                    self.logger.info(f"📊 开始在 {platform_name} 平台执行跟单...")
                    
                    # 更新缩放比例（可能在 Web 界面中被修改）
                    if self.config_manager:
                        scale_ratio = self.config_manager.get_scale_ratio()
                        executor.scale_ratio = scale_ratio
                    
                    # 执行跟单
                    if is_dry_run:
                        # 模拟运行：只记录日志
                        for trade in filtered_trades:
                            self.logger.info(f"🔸 [模拟-{platform_name}] 跟单交易: {trade.get('message', '')}")
                        result = {'success': len(filtered_trades), 'failed': 0, 'details': []}
                    else:
                        # 实际执行
                        result = executor.execute_trades(filtered_trades)
                    
                    results[platform_name] = result
                    self.logger.info(f"✅ {platform_name} 跟单完成: 成功 {result['success']}, 失败 {result['failed']}")
                    
                    # 发送通知
                    if self.config_manager and self.config_manager.load_config().get('notification_on_trade', True):
                        self._send_trade_notification(platform_name, result, filtered_trades, is_dry_run)
                    
                except Exception as e:
                    self.logger.error(f"❌ {platform_name} 平台跟单执行失败: {e}")
                    results[platform_name] = {'success': 0, 'failed': len(filtered_trades), 'error': str(e)}
            
            return results
            
        except Exception as e:
            self.logger.error(f"执行跟单时发生错误: {e}")
            return results
    
    def _filter_whitelist_trades(self, trades: List[Dict]) -> List[Dict]:
        """
        过滤白名单模型的交易
        
        Args:
            trades: 所有交易列表
            
        Returns:
            符合白名单的交易列表
        """
        if not self.config_manager:
            return trades
        
        filtered_trades = []
        whitelist = self.config_manager.get_whitelist_models()
        
        for trade in trades:
            model_id = trade.get('model_id', '')
            trade_message = trade.get('message', '未知交易')
            
            # 检查是否在白名单中
            if self.config_manager.is_model_whitelisted(model_id):
                filtered_trades.append(trade)
                self.logger.info(f"   ✅ [{model_id}] {trade_message}")
            else:
                self.logger.info(f"   ⏭️ [{model_id}] {trade_message} - 不在白名单中")
        
        return filtered_trades
    
    def _send_trade_notification(self, platform_name: str, result: Dict, 
                                 trades: List[Dict], is_dry_run: bool) -> None:
        """
        发送跟单执行结果通知
        
        Args:
            platform_name: 平台名称
            result: 执行结果 {'success': int, 'failed': int}
            trades: 交易列表
            is_dry_run: 是否为模拟运行
        """
        try:
            mode_text = "【模拟运行】" if is_dry_run else ""
            scale_ratio = self.config_manager.get_scale_ratio() if self.config_manager else 0.1
            
            message = (
                f"🤖 **{platform_name.upper()} 跟单执行报告** {mode_text}\n\n"
                f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📊 跟单数量: {len(trades)}\n"
                f"✅ 成功: {result['success']}\n"
                f"❌ 失败: {result['failed']}\n"
                f"📉 缩放比例: {scale_ratio}\n\n"
            )
            
            # 添加交易详情
            for i, trade in enumerate(trades[:5], 1):  # 最多显示 5 个
                message += f"{i}. {trade.get('message', '未知交易')}\n"
            
            if len(trades) > 5:
                message += f"\n... 还有 {len(trades) - 5} 个交易"
            
            # 发送到企业微信
            if self.notifiers['wechat']:
                try:
                    import requests
                    message_data = {"msgtype": "markdown", "markdown": {"content": message}}
                    wechat_url = self.notifiers['wechat']
                    requests.post(wechat_url, json=message_data, 
                                headers={'Content-Type': 'application/json'}, timeout=10)
                except Exception as e:
                    self.logger.error(f"发送 {platform_name} 跟单通知到企业微信失败: {e}")
            
            # 发送到 Telegram
            if self.notifiers['telegram']:
                try:
                    self.notifiers['telegram'].send_plain(message)
                except Exception as e:
                    self.logger.error(f"发送 {platform_name} 跟单通知到 Telegram 失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"发送 {platform_name} 跟单通知时发生错误: {e}")
    
    def get_platform_status(self) -> Dict[str, Dict]:
        """
        获取所有平台状态
        
        Returns:
            {'platform_name': {'enabled': bool, 'scale_ratio': float}, ...}
        """
        status = {}
        for platform_name, platform_info in self.platforms.items():
            executor = platform_info['executor']
            status[platform_name] = {
                'enabled': platform_info['enabled'],
                'scale_ratio': executor.scale_ratio if hasattr(executor, 'scale_ratio') else None,
            }
        return status

