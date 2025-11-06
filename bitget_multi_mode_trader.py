"""
Bitget 多模式交易管理器
支持模拟盘、实盘、双盘同步三种模式
"""
import logging
from typing import Dict, Any, List, Optional
from bitget_trader_ccxt import BitgetTraderCCXT


class BitgetMultiModeTrader:
    """
    Bitget 多模式交易管理器
    
    模式说明：
    - MODE_DEMO_ONLY (0): 只在模拟盘下单
    - MODE_LIVE_ONLY (1): 只在实盘下单
    - MODE_BOTH (2): 模拟盘和实盘同时下单
    """
    
    # 交易模式常量
    MODE_DEMO_ONLY = 0  # 只在模拟盘
    MODE_LIVE_ONLY = 1  # 只在实盘
    MODE_BOTH = 2       # 模拟盘和实盘都执行
    
    def __init__(self, 
                 mode: int = MODE_DEMO_ONLY,
                 # 实盘配置
                 live_api_key: Optional[str] = None,
                 live_secret_key: Optional[str] = None,
                 live_passphrase: Optional[str] = None,
                 # 模拟盘配置
                 demo_api_key: Optional[str] = None,
                 demo_secret_key: Optional[str] = None,
                 demo_passphrase: Optional[str] = None,
                 # 通用配置
                 scale_ratio: float = 0.1):
        """
        初始化多模式交易管理器
        
        Args:
            mode: 交易模式 (0=模拟盘, 1=实盘, 2=双盘)
            live_api_key: 实盘 API Key
            live_secret_key: 实盘 Secret Key
            live_passphrase: 实盘 Passphrase
            demo_api_key: 模拟盘 API Key
            demo_secret_key: 模拟盘 Secret Key
            demo_passphrase: 模拟盘 Passphrase
            scale_ratio: 交易量缩放比例
        """
        self.mode = mode
        self.scale_ratio = scale_ratio
        self.logger = logging.getLogger(__name__)
        
        self.live_trader = None
        self.demo_trader = None
        
        # 根据模式初始化相应的交易器
        if mode == self.MODE_LIVE_ONLY or mode == self.MODE_BOTH:
            # 需要实盘交易器
            if not all([live_api_key, live_secret_key, live_passphrase]):
                raise ValueError("实盘模式需要配置实盘 API 密钥")
            
            self.logger.info("初始化实盘交易器...")
            self.live_trader = BitgetTraderCCXT(
                api_key=live_api_key,
                secret_key=live_secret_key,
                passphrase=live_passphrase,
                scale_ratio=scale_ratio,
                env_name='实盘'
            )
            self.live_trader.load_markets()
            self.logger.info("✅ 实盘交易器初始化完成")
        
        if mode == self.MODE_DEMO_ONLY or mode == self.MODE_BOTH:
            # 需要模拟盘交易器
            if not all([demo_api_key, demo_secret_key, demo_passphrase]):
                raise ValueError("模拟盘模式需要配置模拟盘 API 密钥")
            
            self.logger.info("初始化模拟盘交易器...")
            self.demo_trader = BitgetTraderCCXT(
                api_key=demo_api_key,
                secret_key=demo_secret_key,
                passphrase=demo_passphrase,
                scale_ratio=scale_ratio,
                env_name='模拟盘'
            )
            self.demo_trader.load_markets()
            self.logger.info("✅ 模拟盘交易器初始化完成")
        
        # 记录当前模式
        mode_names = {
            self.MODE_DEMO_ONLY: "模拟盘",
            self.MODE_LIVE_ONLY: "实盘",
            self.MODE_BOTH: "双盘同步"
        }
        self.logger.info(f"🎯 交易模式: {mode_names.get(mode, '未知')} (mode={mode})")
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return 'bitget'
    
    def test_connection(self) -> bool:
        """
        测试连接
        
        Returns:
            成功返回 True，失败返回 False
        """
        success = True
        
        if self.live_trader:
            self.logger.info("测试实盘连接...")
            if not self.live_trader.test_connection():
                self.logger.error("❌ 实盘连接测试失败")
                success = False
            else:
                self.logger.info("✅ 实盘连接测试成功")
        
        if self.demo_trader:
            self.logger.info("测试模拟盘连接...")
            if not self.demo_trader.test_connection():
                self.logger.error("❌ 模拟盘连接测试失败")
                success = False
            else:
                self.logger.info("✅ 模拟盘连接测试成功")
        
        return success
    
    def execute_trades(self, trades: List[Dict], dry_run: bool = False) -> Dict[str, Any]:
        """
        执行交易（根据模式在不同环境下单）
        
        Args:
            trades: 交易列表
            dry_run: 是否模拟运行
            
        Returns:
            执行结果字典，包含各环境的执行结果
        """
        results = {}
        
        # 模拟盘执行
        if self.demo_trader and (self.mode == self.MODE_DEMO_ONLY or self.mode == self.MODE_BOTH):
            self.logger.info("=" * 60)
            self.logger.info("📱 开始在模拟盘执行交易...")
            self.logger.info("=" * 60)
            demo_result = self.demo_trader.execute_trades(trades, dry_run=dry_run)
            results['demo'] = demo_result
            self.logger.info(f"模拟盘执行完成: 成功 {demo_result.get('success', 0)}, 失败 {demo_result.get('failed', 0)}")
        
        # 实盘执行
        if self.live_trader and (self.mode == self.MODE_LIVE_ONLY or self.mode == self.MODE_BOTH):
            self.logger.info("=" * 60)
            self.logger.info("💰 开始在实盘执行交易...")
            self.logger.info("=" * 60)
            live_result = self.live_trader.execute_trades(trades, dry_run=dry_run)
            results['live'] = live_result
            self.logger.info(f"实盘执行完成: 成功 {live_result.get('success', 0)}, 失败 {live_result.get('failed', 0)}")
        
        # 汇总结果
        total_success = sum(r.get('success', 0) for r in results.values())
        total_failed = sum(r.get('failed', 0) for r in results.values())
        
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info(f"📊 多模式交易执行完成")
        self.logger.info(f"   总成功: {total_success}, 总失败: {total_failed}")
        self.logger.info("=" * 60)
        
        return {
            'mode': self.mode,
            'results': results,
            'total_success': total_success,
            'total_failed': total_failed
        }
    
    def place_order(self, symbol: str, side: str, order_type: str, amount: float,
                   price: Optional[float] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        下单（在所有激活的环境下单）
        
        Returns:
            各环境的订单结果
        """
        results = {}
        
        if self.demo_trader and (self.mode == self.MODE_DEMO_ONLY or self.mode == self.MODE_BOTH):
            self.logger.info("📱 模拟盘下单...")
            demo_order = self.demo_trader.place_order(symbol, side, order_type, amount, price, params)
            results['demo'] = demo_order
        
        if self.live_trader and (self.mode == self.MODE_LIVE_ONLY or self.mode == self.MODE_BOTH):
            self.logger.info("💰 实盘下单...")
            live_order = self.live_trader.place_order(symbol, side, order_type, amount, price, params)
            results['live'] = live_order
        
        return results
    
    def get_position(self, symbol: str) -> Dict[str, Any]:
        """
        查询持仓（从所有激活的环境查询）
        
        Returns:
            各环境的持仓信息
        """
        results = {}
        
        if self.demo_trader and (self.mode == self.MODE_DEMO_ONLY or self.mode == self.MODE_BOTH):
            demo_position = self.demo_trader.get_position(symbol)
            results['demo'] = demo_position
        
        if self.live_trader and (self.mode == self.MODE_LIVE_ONLY or self.mode == self.MODE_BOTH):
            live_position = self.live_trader.get_position(symbol)
            results['live'] = live_position
        
        return results
    
    def close_all_positions(self, symbol: str, side: Optional[str] = None) -> Dict[str, bool]:
        """
        平掉所有持仓（在所有激活的环境）
        
        Returns:
            各环境的执行结果
        """
        results = {}
        
        if self.demo_trader and (self.mode == self.MODE_DEMO_ONLY or self.mode == self.MODE_BOTH):
            self.logger.info("📱 模拟盘平仓...")
            results['demo'] = self.demo_trader.close_all_positions(symbol, side)
        
        if self.live_trader and (self.mode == self.MODE_LIVE_ONLY or self.mode == self.MODE_BOTH):
            self.logger.info("💰 实盘平仓...")
            results['live'] = self.live_trader.close_all_positions(symbol, side)
        
        return results

