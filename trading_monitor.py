"""
定时任务调度模块
负责管理定时获取持仓数据和监控任务
"""
import logging
import schedule
import time
from typing import Optional, List, Dict
from datetime import datetime

from position_fetcher import PositionDataFetcher
from trade_analyzer import TradeAnalyzer
from wechat_notifier import WeChatNotifier
from config_manager import ConfigManager
from bitget_trader_ccxt import BitgetTraderCCXT


class TelegramNotifier:
    """Telegram 通知器"""

    def __init__(self, bot_token: str, chat_id: str, proxy: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.proxy = proxy
        self.logger = logging.getLogger(__name__)

    def _send_text(self, text: str) -> bool:
        try:
            import requests

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            proxies = None
            if self.proxy:
                host, port = self.proxy.split(":") if ":" in self.proxy else (self.proxy, "7890")
                proxies = {
                    "http": f"http://{host}:{port}",
                    "https": f"http://{host}:{port}",
                }
            resp = requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=15, proxies=proxies)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                self.logger.error(f"Telegram 发送失败: {data}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Telegram 发送消息错误: {e}")
            return False

    def send_trade_notification(self, content: str) -> bool:
        return self._send_text(content)

    def send_plain(self, text: str) -> bool:
        return self._send_text(text)


class TradingMonitor:
    """交易监控器"""
    
    def __init__(self, api_url: str, wechat_webhook_url: Optional[str] = None, telegram_bot_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None, telegram_proxy: Optional[str] = None,
                 monitored_models: Optional[List[str]] = None, save_history_data: bool = False,
                 bitget_api_key: Optional[str] = None, bitget_secret_key: Optional[str] = None,
                 bitget_passphrase: Optional[str] = None, bitget_api_url: Optional[str] = None):
        """
        初始化交易监控器
        
        Args:
            api_url: API接口地址
            webhook_url: 企业微信机器人webhook地址
            monitored_models: 要监控的模型列表，None表示监控所有模型
            save_history_data: 是否保存历史数据到data目录，默认为False
            bitget_api_key: Bitget API Key
            bitget_secret_key: Bitget Secret Key
            bitget_passphrase: Bitget Passphrase
            bitget_api_url: Bitget API URL
        """
        self.api_url = api_url
        self.wechat_webhook_url = wechat_webhook_url
        self.monitored_models = monitored_models
        
        # 初始化各个组件
        self.position_fetcher = PositionDataFetcher(api_url, save_history_data)
        self.trade_analyzer = TradeAnalyzer()
        self.wechat_notifier = WeChatNotifier(wechat_webhook_url) if wechat_webhook_url else None
        self.telegram_notifier = None
        if telegram_bot_token and telegram_chat_id:
            self.telegram_notifier = TelegramNotifier(telegram_bot_token, telegram_chat_id, telegram_proxy)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化 Bitget 交易器
        self.bitget_trader = None
        if bitget_api_key and bitget_secret_key and bitget_passphrase:
            scale_ratio = self.config_manager.get_scale_ratio()
            # 根据 API Key 判断是实盘还是模拟盘
            env_name = '模拟盘' if 'demo' in str(bitget_api_key).lower() else '实盘'
            self.bitget_trader = BitgetTraderCCXT(
                api_key=bitget_api_key,
                secret_key=bitget_secret_key,
                passphrase=bitget_passphrase,
                scale_ratio=scale_ratio,
                env_name=env_name
            )
            # load_markets 会在初始化时自动调用，这里不需要再调用
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"Bitget 交易器已初始化，缩放比例: {scale_ratio}, 环境: {env_name}")
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.info("Bitget API 未配置，自动跟单功能未启用")
        
        # 设置定时任务
        self._setup_schedule()
    
    def _setup_schedule(self):
        """设置定时任务"""
        # 每分钟执行一次监控任务
        schedule.every().minute.do(self._monitor_task)
        
        self.logger.info("定时任务已设置：每分钟执行一次监控")
    
    def _execute_bitget_follow_trades(self, trades: List[Dict]) -> None:
        """
        执行 Bitget 自动跟单
        
        Args:
            trades: 交易变化列表
        """
        try:
            # 检查是否启用自动跟单
            if not self.config_manager.get_enabled():
                self.logger.debug("Bitget 自动跟单未启用，跳过")
                return
            
            # 检查是否配置了 Bitget 交易器
            if not self.bitget_trader:
                self.logger.warning("Bitget 交易器未初始化，无法执行跟单")
                return
            
            # 检查是否为模拟运行模式
            is_dry_run = self.config_manager.is_dry_run()
            if is_dry_run:
                self.logger.info("🔸 模拟运行模式：只记录日志，不实际下单")
            
            # 过滤白名单模型
            filtered_trades = []
            whitelist = self.config_manager.get_whitelist_models()
            
            for trade in trades:
                model_id = trade.get('model_id', '')
                
                # 检查是否在白名单中
                if self.config_manager.is_model_whitelisted(model_id):
                    filtered_trades.append(trade)
                    self.logger.info(f"✅ 模型 {model_id} 在白名单中，准备跟单")
                else:
                    self.logger.info(f"⏭️ 模型 {model_id} 不在白名单中，跳过跟单")
            
            if not filtered_trades:
                self.logger.info("没有符合白名单条件的交易，跳过跟单")
                return
            
            self.logger.info(f"准备执行 {len(filtered_trades)} 个跟单交易（白名单: {whitelist or '全部'}）")
            
            # 更新缩放比例（可能在 Web 界面中被修改）
            scale_ratio = self.config_manager.get_scale_ratio()
            self.bitget_trader.scale_ratio = scale_ratio
            
            # 执行跟单
            if is_dry_run:
                # 模拟运行：只记录日志
                for trade in filtered_trades:
                    self.logger.info(f"🔸 [模拟] 跟单交易: {trade.get('message', '')}")
                result = {'success': len(filtered_trades), 'failed': 0}
            else:
                # 实际执行
                result = self.bitget_trader.execute_trades(filtered_trades)
            
            # 发送跟单执行结果通知
            if self.config_manager.load_config().get('notification_on_trade', True):
                self._send_bitget_trade_notification(result, filtered_trades, is_dry_run)
            
            self.logger.info(f"Bitget 跟单执行完成: 成功 {result['success']}, 失败 {result['failed']}")
            
        except Exception as e:
            self.logger.error(f"执行 Bitget 跟单时发生错误: {e}")
    
    def _send_bitget_trade_notification(self, result: Dict, trades: List[Dict], is_dry_run: bool) -> None:
        """
        发送 Bitget 跟单执行结果通知
        
        Args:
            result: 执行结果 {'success': int, 'failed': int}
            trades: 交易列表
            is_dry_run: 是否为模拟运行
        """
        try:
            mode_text = "【模拟运行】" if is_dry_run else ""
            message = (
                f"🤖 **Bitget 跟单执行报告** {mode_text}\n\n"
                f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📊 跟单数量: {len(trades)}\n"
                f"✅ 成功: {result['success']}\n"
                f"❌ 失败: {result['failed']}\n"
                f"📉 缩放比例: {self.config_manager.get_scale_ratio()}\n\n"
            )
            
            # 添加交易详情
            for i, trade in enumerate(trades[:5], 1):  # 最多显示 5 个
                message += f"{i}. {trade.get('message', '未知交易')}\n"
            
            if len(trades) > 5:
                message += f"\n... 还有 {len(trades) - 5} 个交易"
            
            # 发送到各个通知渠道
            if self.wechat_notifier:
                try:
                    import requests
                    message_data = {"msgtype": "markdown", "markdown": {"content": message}}
                    requests.post(self.wechat_webhook_url, json=message_data, 
                                headers={'Content-Type': 'application/json'}, timeout=10)
                except Exception as e:
                    self.logger.error(f"发送 Bitget 跟单通知到企业微信失败: {e}")
            
            if self.telegram_notifier:
                try:
                    self.telegram_notifier.send_plain(message)
                except Exception as e:
                    self.logger.error(f"发送 Bitget 跟单通知到 Telegram 失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"发送 Bitget 跟单通知时发生错误: {e}")
    
    def _monitor_task(self):
        """
        监控任务主函数
        每分钟执行一次，获取持仓数据并分析变化
        """
        try:
            self.logger.info("开始执行监控任务")
            
            # 1. 获取当前持仓数据
            current_data = self.position_fetcher.fetch_positions()
            if not current_data:
                self.logger.info("获取持仓数据失败或为空，跳过本次监控")
                return
            
            # 2. 保存当前数据
            if not self.position_fetcher.save_positions(current_data, "current.json"):
                self.logger.error("保存当前持仓数据失败")
                return
            
            # 3. 检查是否存在上次数据
            last_data = self.position_fetcher.load_positions("last.json")
            if not last_data:
                self.logger.info("首次运行，无历史数据可比较")
                # 将当前数据重命名为历史数据，为下次比较做准备
                self.position_fetcher.rename_current_to_last()
                self.logger.info("监控任务执行完成（首次运行）")
                return
            
            # 4. 分析持仓变化
            self.logger.info(f"开始分析持仓变化，上次数据包含 {len(last_data.get('positions', []))} 个模型")
            self.logger.info(f"当前数据包含 {len(current_data.get('positions', []))} 个模型")
            
            trades = self.trade_analyzer.analyze_position_changes(
                last_data, current_data, self.monitored_models
            )
            
            # 5. 如果有交易变化，发送通知
            if trades:
                self.logger.info(f"检测到 {len(trades)} 个交易变化，准备发送通知")
                
                # 打印交易摘要到日志
                summary = self.trade_analyzer.generate_trade_summary(trades)
                self.logger.info(f"交易详情:\n{summary}")
                
                # 发送通知（各渠道按配置发送）
                sent_any = False
                content = self.trade_analyzer.generate_trade_summary(trades)
                content = content + "\n\n🔗 全部持仓: http://alpha.insightpearl.com/"
                if self.wechat_notifier:
                    try:
                        if self.wechat_notifier.send_trade_notification(trades):
                            sent_any = True
                    except Exception:
                        self.logger.error("企业微信通知发送失败")
                if self.telegram_notifier:
                    try:
                        if self.telegram_notifier.send_trade_notification(content):
                            sent_any = True
                    except Exception:
                        self.logger.error("Telegram 通知发送失败")
                if sent_any:
                    self.logger.info("交易通知发送完成（至少一个渠道成功）")
                else:
                    self.logger.warning("未配置通知渠道或所有渠道发送失败")
                
                # 6. Bitget 自动跟单（在通知发送后执行）
                self._execute_bitget_follow_trades(trades)
            else:
                self.logger.info("无交易变化")
            
            # 6. 将当前数据重命名为历史数据（只有在成功处理数据后才重命名）
            self.position_fetcher.rename_current_to_last()
            
            self.logger.info("监控任务执行完成")
            
        except Exception as e:
            self.logger.error(f"执行监控任务时发生错误: {e}")
    
    def start_monitoring(self):
        """
        开始监控
        启动定时任务并持续运行
        """
        self.logger.info("开始启动交易监控系统")
        
        # 发送启动通知
        try:
            startup_message = (
                "🚀 **AI交易监控系统启动**\n\n"
                f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🔗 API地址: {self.api_url}\n"
                f"👀 监控模型: {', '.join(self.monitored_models) if self.monitored_models else '全部模型'}\n\n"
                "✅ 系统已开始监控，将每分钟检查一次持仓变化"
            )
            if self.wechat_notifier:
                import requests
                message_data = {"msgtype": "markdown", "markdown": {"content": startup_message}}
                requests.post(self.wechat_webhook_url, json=message_data, headers={'Content-Type': 'application/json'}, timeout=10)
            if self.telegram_notifier:
                self.telegram_notifier.send_plain(startup_message)
            self.logger.info("启动通知发送完成（按配置渠道）")
        except Exception as e:
            self.logger.warning(f"发送启动通知时发生错误: {e}")
        
        # 开始定时任务循环
        self.logger.info("定时任务循环已启动")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在关闭监控系统...")
            self._send_shutdown_notification()
        except Exception as e:
            self.logger.error(f"监控系统运行时发生错误: {e}")
            self._send_error_notification(str(e))
    
    def _send_shutdown_notification(self):
        """发送关闭通知"""
        try:
            shutdown_message = (
                "🛑 **AI交易监控系统关闭**\n\n"
                f"⏰ 关闭时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "系统已安全关闭"
            )
            
            if self.wechat_notifier:
                import requests
                message_data = {"msgtype": "markdown", "markdown": {"content": shutdown_message}}
                requests.post(self.wechat_webhook_url, json=message_data, headers={'Content-Type': 'application/json'}, timeout=10)
            if self.telegram_notifier:
                self.telegram_notifier.send_plain(shutdown_message)
            self.logger.info("关闭通知发送完成（按配置渠道）")
            
        except Exception as e:
            self.logger.warning(f"发送关闭通知时发生错误: {e}")
    
    def _send_error_notification(self, error_message: str):
        """发送错误通知"""
        try:
            error_notification = (
                "❌ **AI交易监控系统错误**\n\n"
                f"⏰ 错误时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🚨 错误信息: {error_message}\n\n"
                "请检查系统状态"
            )
            
            if self.wechat_notifier:
                import requests
                message_data = {"msgtype": "markdown", "markdown": {"content": error_notification}}
                requests.post(self.wechat_webhook_url, json=message_data, headers={'Content-Type': 'application/json'}, timeout=10)
            if self.telegram_notifier:
                self.telegram_notifier.send_plain(error_notification)
            self.logger.info("错误通知发送完成（按配置渠道）")
            
        except Exception as e:
            self.logger.error(f"发送错误通知时发生错误: {e}")
    
    def test_notification(self):
        """测试通知功能"""
        self.logger.info("测试通知功能")
        ok = True
        if self.wechat_notifier:
            ok = ok and self.wechat_notifier.send_test_message()
        if self.telegram_notifier:
            ok = ok and self.telegram_notifier.send_plain("🧪 AI交易监控系统测试\n\n✅ Telegram 通道正常")
        return ok
