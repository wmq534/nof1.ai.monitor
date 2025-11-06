"""
Bitget 交易器 - 使用 CCXT 库实现
支持 U 本位合约交易，包括开仓、平仓、止盈止损等功能
"""
import logging
import ccxt
from typing import Dict, List, Optional, Any


class BitgetTraderCCXT:
    """
    Bitget 交易器（基于 CCXT）
    
    功能：
    - 市价开仓/平仓
    - 设置止盈止损
    - 持仓查询
    - 批量交易执行
    - 支持模拟盘/实盘切换
    """
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, 
                 scale_ratio: float = 1.0, env_name: str = '交易'):
        """
        初始化 Bitget 交易器
        
        Args:
            api_key: API Key
            secret_key: Secret Key
            passphrase: Passphrase
            scale_ratio: 交易量缩放比例（默认 1.0 = 100%）
            env_name: 环境名称（用于日志显示，如"实盘"、"模拟盘"）
        """
        self.logger = logging.getLogger(__name__)
        self.scale_ratio = scale_ratio
        self.env_name = env_name
        
        # 初始化 CCXT Bitget 交易所
        self.exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # U 本位合约
                'defaultSubType': 'linear',  # 正向合约（USDT 本位）
            }
        })
        
        # 如果是模拟盘环境，设置沙盒模式
        if 'demo' in env_name.lower() or '模拟' in env_name:
            self.exchange.set_sandbox_mode(True)
            self.logger.info("🔸 已启用沙盒模式（模拟盘环境）")
        
        self.logger.info(f"✅ Bitget 交易器初始化完成 (CCXT v{ccxt.__version__})")
        self.logger.info(f"   缩放比例: {scale_ratio}")
        self.logger.info(f"   环境: {env_name}")
        
        # 自动设置为单向持仓模式
        try:
            # 先加载市场信息（某些 API 调用需要）
            self.exchange.load_markets()
            # 设置持仓模式为单向持仓 (hedged=False)
            self.exchange.set_position_mode(hedged=False)
            self.logger.info("🔧 已自动设置为单向持仓模式")
        except Exception as e:
            # 如果设置失败，记录警告但不中断
            self.logger.warning(f"⚠️  设置持仓模式失败（可能已是单向持仓）: {e}")
            # 继续执行，稍后会再次调用 load_markets
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return 'bitget'
    
    def load_markets(self):
        """加载市场信息（如果尚未加载）"""
        try:
            if not self.exchange.markets:
                self.exchange.load_markets()
                self.logger.info("✅ 市场信息加载完成")
            else:
                self.logger.debug("市场信息已加载，跳过")
        except Exception as e:
            self.logger.error(f"❌ 加载市场信息失败: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        测试连接
        
        Returns:
            连接成功返回 True，失败返回 False
        """
        try:
            # 获取账户余额来测试连接
            balance = self.exchange.fetch_balance()
            self.logger.info(f"✅ [{self.env_name}] 连接测试成功")
            
            # 显示余额信息
            if 'USDT' in balance.get('total', {}):
                usdt_balance = balance['total']['USDT']
                self.logger.info(f"   USDT 余额: {usdt_balance:.2f}")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ [{self.env_name}] 连接测试失败: {e}")
            return False
    
    def place_order(self, symbol: str, side: str, order_type: str, amount: float,
                   price: Optional[float] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        下单
        
        Args:
            symbol: 交易对，如 'BTC/USDT:USDT'
            side: 方向，'buy' 或 'sell'
            order_type: 订单类型，'market' 或 'limit'
            amount: 数量（币的数量，不是 USDT）
            price: 价格（限价单需要）
            params: 额外参数，如 {'reduceOnly': True}
            
        Returns:
            订单信息，失败返回 None
        """
        try:
            # 合并参数
            order_params = params or {}
            
            # 判断是开仓还是平仓
            is_reduce_only = order_params.get('reduceOnly', False)
            
            # Bitget 单向持仓模式：只设置 holdSide，不设置 tradeSide
            # tradeSide 可能与某些设置冲突，让 Bitget 根据 holdSide 和 reduceOnly 自动判断
            if 'holdSide' not in order_params:
                if is_reduce_only:
                    # 平仓：holdSide 表示要平的仓位方向
                    if side == 'sell':
                        order_params['holdSide'] = 'long'   # 卖出平多仓
                    elif side == 'buy':
                        order_params['holdSide'] = 'short'  # 买入平空仓
                else:
                    # 开仓：holdSide 表示要开的仓位方向
                    if side == 'buy':
                        order_params['holdSide'] = 'long'
                    elif side == 'sell':
                        order_params['holdSide'] = 'short'
            
            self.logger.info(f"准备下单: {symbol} {side} {order_type} {amount}")
            self.logger.info(f"下单参数: side={side}, holdSide={order_params.get('holdSide')}, "
                           f"positionSide={order_params.get('positionSide')}, "
                           f"tradeSide={order_params.get('tradeSide')}, "
                           f"reduceOnly={order_params.get('reduceOnly', False)}")
            
            # 下单
            if order_type == 'market':
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=amount,
                    params=order_params
                )
            else:
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side=side,
                    amount=amount,
                    price=price,
                    params=order_params
                )
            
            self.logger.info(f"✅ [{self.env_name}] 下单成功，订单ID: {order.get('id')}")
            return order
            
        except Exception as e:
            self.logger.error(f"❌ [{self.env_name}] 下单失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_position(self, symbol: str) -> List[Dict]:
        """
        查询持仓
        
        Args:
            symbol: 交易对，如 'BTC/USDT:USDT'
            
        Returns:
            持仓列表
        """
        try:
            positions = self.exchange.fetch_positions([symbol])
            # 过滤出有持仓的
            active_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]
            return active_positions
        except Exception as e:
            self.logger.error(f"❌ [{self.env_name}] 查询持仓失败: {e}")
            return []
    
    def set_take_profit_stop_loss(self, symbol: str, side: str, amount: float,
                                  take_profit_price: Optional[float] = None,
                                  stop_loss_price: Optional[float] = None) -> Dict[str, Any]:
        """
        设置止盈止损
        
        Args:
            symbol: 交易对
            side: 平仓方向（平多用 'sell'，平空用 'buy'）
            amount: 数量
            take_profit_price: 止盈价格
            stop_loss_price: 止损价格
            
        Returns:
            结果字典 {'take_profit': order, 'stop_loss': order}
        """
        result = {}
        
        # 确定持仓方向（平仓时，side和持仓方向相反）
        # side='sell' 表示平多仓，hold/positionSide='long'
        # side='buy' 表示平空仓，hold/positionSide='short'
        position_side = 'long' if side == 'sell' else 'short'
        
        # Bitget 止盈止损订单是计划委托，参数设置不同
        # 止盈订单：triggerType='fill_price' 表示按标记价格触发
        if take_profit_price:
            try:
                tp_order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=amount,
                    params={
                        'triggerPrice': take_profit_price,  # 触发价格
                        'triggerType': 'fill_price',  # 按标记价格触发
                        'reduceOnly': True
                    }
                )
                result['take_profit'] = tp_order
                self.logger.info(f"✅ [{self.env_name}] 止盈订单设置成功: {take_profit_price}")
            except Exception as e:
                self.logger.error(f"❌ [{self.env_name}] 止盈订单失败: {e}")
        
        # 止损订单：triggerType='fill_price' 表示按标记价格触发
        if stop_loss_price:
            try:
                sl_order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=amount,
                    params={
                        'triggerPrice': stop_loss_price,  # 触发价格
                        'triggerType': 'fill_price',  # 按标记价格触发
                        'reduceOnly': True
                    }
                )
                result['stop_loss'] = sl_order
                self.logger.info(f"✅ [{self.env_name}] 止损订单设置成功: {stop_loss_price}")
            except Exception as e:
                self.logger.error(f"❌ [{self.env_name}] 止损订单失败: {e}")
        
        return result
    
    def close_all_positions(self, symbol: str, side: Optional[str] = None) -> bool:
        """
        平掉所有持仓
        
        Args:
            symbol: 交易对
            side: 指定方向（可选，None 表示平掉所有方向）
            
        Returns:
            成功返回 True，失败返回 False
        """
        try:
            positions = self.get_position(symbol)
            
            if not positions:
                self.logger.info(f"[{self.env_name}] {symbol} 无持仓")
                return False
            
            for position in positions:
                pos_side = position.get('side')  # 'long' 或 'short'
                pos_amount = float(position.get('contracts', 0))
                
                # 如果指定了方向，只平指定方向的仓位
                if side and pos_side != side:
                    continue
                
                if pos_amount > 0:
                    # 平多仓用 sell，平空仓用 buy
                    close_side = 'sell' if pos_side == 'long' else 'buy'
                    
                    self.logger.info(f"[{self.env_name}] 平仓 {symbol} {pos_side} {pos_amount}")
                    
                    order = self.place_order(
                        symbol=symbol,
                        side=close_side,
                        order_type='market',
                        amount=pos_amount,
                        params={'reduceOnly': True}
                    )
                    
                    if order:
                        self.logger.info(f"✅ [{self.env_name}] 平仓成功")
                    else:
                        self.logger.error(f"❌ [{self.env_name}] 平仓失败")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ [{self.env_name}] 平仓过程出错: {e}")
            return False
    
    def execute_trades(self, trades: List[Dict], dry_run: bool = False) -> Dict[str, int]:
        """
        批量执行交易
        
        Args:
            trades: 交易列表，每个交易包含:
                - symbol: 币种符号（如 'BTC'）
                - action: 操作类型（如 '减多', '加多', '开多', '平多'）
                - quantity: 数量
                - direction: 方向（'long' 或 'short'）
                - profit_target: 止盈价格（可选）
                - stop_loss: 止损价格（可选）
            dry_run: 是否模拟运行（True=只打印不下单）
            
        Returns:
            执行结果 {'success': 成功数, 'failed': 失败数}
        """
        success_count = 0
        failed_count = 0
        
        for i, trade in enumerate(trades, 1):
            try:
                symbol_base = trade.get('symbol', '').upper()
                action = trade.get('action', '')
                quantity = float(trade.get('quantity', 0))
                direction = trade.get('direction', 'long')
                tp = trade.get('profit_target')
                sl = trade.get('stop_loss')
                
                # 构建 CCXT 格式的交易对
                symbol = f"{symbol_base}/USDT:USDT"
                
                # 缩放数量
                scaled_quantity = quantity * self.scale_ratio
                
                self.logger.info("")
                self.logger.info(f"{'=' * 60}")
                self.logger.info(f"[{self.env_name}] 交易 {i}/{len(trades)}: {symbol_base} {action}")
                self.logger.info(f"{'=' * 60}")
                self.logger.info(f"原始数量: {quantity}")
                self.logger.info(f"缩放后数量: {scaled_quantity} (比例: {self.scale_ratio})")
                self.logger.info(f"方向: {direction}")
                self.logger.info(f"止盈: {tp}")
                self.logger.info(f"止损: {sl}")
                
                # 检查数量是否有效
                if quantity <= 0 or scaled_quantity <= 0:
                    self.logger.warning(f"⚠️ [{self.env_name}] 跳过：数量为 0 或负数")
                    success_count += 1  # 算作成功，因为这不是错误
                    continue
                
                # 检查缩放后的数量是否太小（低于交易所最小精度）
                # 大多数交易所要求至少 0.0001 或更大的数量
                if scaled_quantity < 0.0001:
                    self.logger.warning(f"⚠️ [{self.env_name}] 跳过：缩放后数量太小 ({scaled_quantity})，建议增加缩放比例")
                    success_count += 1
                    continue
                
                if dry_run:
                    self.logger.info("🔸 [模拟模式] 跳过实际下单")
                    success_count += 1
                    continue
                
                # 判断操作类型
                is_open = '开' in action  # 开仓
                is_close = '平' in action  # 平仓
                is_add = '加' in action   # 加仓
                is_reduce = '减' in action  # 减仓
                
                is_long = direction == 'long' or '多' in action
                is_short = direction == 'short' or '空' in action
                
                # 执行操作
                if is_close:
                    # 平仓
                    close_side = 'sell' if is_long else 'buy'
                    order = self.place_order(
                        symbol=symbol,
                        side=close_side,
                        order_type='market',
                        amount=scaled_quantity,
                        params={'reduceOnly': True}
                    )
                    if order:
                        success_count += 1
                    else:
                        failed_count += 1
                
                elif is_open:
                    # 开仓
                    open_side = 'buy' if is_long else 'sell'
                    
                    # 验证止盈止损
                    if not tp or tp == 'N/A' or not sl or sl == 'N/A':
                        self.logger.error(f"⛔ [{self.env_name}] 拒绝开仓 {symbol}: 缺少止盈或止损！")
                        self.logger.error(f"⛔ 风险控制：不允许没有止盈止损的仓位存在！")
                        failed_count += 1
                        continue
                    
                    # 开仓
                    order = self.place_order(
                        symbol=symbol,
                        side=open_side,
                        order_type='market',
                        amount=scaled_quantity
                    )
                    
                    if order:
                        # 设置止盈止损
                        tp_price = float(tp) if tp and tp != 'N/A' else None
                        sl_price = float(sl) if sl and sl != 'N/A' else None
                        
                        close_side = 'sell' if is_long else 'buy'
                        tp_sl_result = self.set_take_profit_stop_loss(
                            symbol=symbol,
                            side=close_side,
                            amount=scaled_quantity,
                            take_profit_price=tp_price,
                            stop_loss_price=sl_price
                        )
                        
                        if tp_sl_result.get('stop_loss'):
                            success_count += 1
                        else:
                            self.logger.error(f"❌ [{self.env_name}] 止损设置失败！")
                            failed_count += 1
                    else:
                        failed_count += 1
                
                elif is_add or is_reduce:
                    # 加仓或减仓
                    if is_add:
                        # 加仓 = 买入（多）或卖出（空）
                        order_side = 'buy' if is_long else 'sell'
                        order = self.place_order(
                            symbol=symbol,
                            side=order_side,
                            order_type='market',
                            amount=scaled_quantity
                        )
                    else:
                        # 减仓 = 卖出（多）或买入（空）
                        order_side = 'sell' if is_long else 'buy'
                        order = self.place_order(
                            symbol=symbol,
                            side=order_side,
                            order_type='market',
                            amount=scaled_quantity,
                            params={'reduceOnly': True}
                        )
                    
                    if order:
                        success_count += 1
                    else:
                        failed_count += 1
                
                else:
                    self.logger.warning(f"⚠️ [{self.env_name}] 未识别的操作类型: {action}")
                    failed_count += 1
                
            except Exception as e:
                self.logger.error(f"❌ [{self.env_name}] 执行交易失败: {e}")
                import traceback
                traceback.print_exc()
                failed_count += 1
        
        return {
            'success': success_count,
            'failed': failed_count
        }
