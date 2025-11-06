#!/usr/bin/env python3
"""
Bitget 交易功能测试脚本

用法:
  python test_bitget_trading.py              # 模拟所有减仓操作
  python test_bitget_trading.py --single 0   # 模拟单个减仓
  python test_bitget_trading.py --real       # 实际执行所有减仓
  python test_bitget_trading.py --real --single 0  # 实际执行单个减仓
  
  python test_bitget_trading.py --open       # 模拟开仓
  python test_bitget_trading.py --real --open  # 实际开仓
  
  python test_bitget_trading.py --add        # 模拟加仓
  python test_bitget_trading.py --real --add   # 实际加仓
  
  python test_bitget_trading.py --reduce     # 模拟减仓
  python test_bitget_trading.py --real --reduce # 实际减仓
  
  python test_bitget_trading.py --close      # 模拟平仓
  python test_bitget_trading.py --real --close  # 实际平仓
  
  python test_bitget_trading.py --flow       # 模拟完整流程
  python test_bitget_trading.py --real --flow   # 实际完整流程
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
from bitget_trader_ccxt import BitgetTraderCCXT
from bitget_multi_mode_trader import BitgetMultiModeTrader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# 测试数据：从日志中提取的实际减仓交易
TEST_TRADES = [
    {
        'model_name': 'DeepSeek V3', 'symbol': 'SOL', 'action': '减多',
        'quantity': 4.43, 'direction': 'long', 'profit_target': '266', 'stop_loss': '227',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'ONDO', 'action': '减多',
        'quantity': 1196.8, 'direction': 'long', 'profit_target': '1.67', 'stop_loss': '1.45',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'LINK', 'action': '减多',
        'quantity': 16.64, 'direction': 'long', 'profit_target': '21.79', 'stop_loss': '18.91',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'AAVE', 'action': '减多',
        'quantity': 1.33, 'direction': 'long', 'profit_target': '405', 'stop_loss': '351',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'ARB', 'action': '减多',
        'quantity': 38.72, 'direction': 'long', 'profit_target': '1.149', 'stop_loss': '0.997',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'SUI', 'action': '减多',
        'quantity': 80.19, 'direction': 'long', 'profit_target': '4.81', 'stop_loss': '4.23',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'DOGE', 'action': '减多',
        'quantity': 1116.37, 'direction': 'long', 'profit_target': '0.41', 'stop_loss': '0.36',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'TIA', 'action': '减多',
        'quantity': 36.21, 'direction': 'long', 'profit_target': '9.01', 'stop_loss': '7.73',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'WLD', 'action': '减多',
        'quantity': 63.94, 'direction': 'long', 'profit_target': '4.31', 'stop_loss': '3.72',
        'timestamp': '2025-11-05T10:25:59.155184'
    },
    {
        'model_name': 'DeepSeek V3', 'symbol': 'SEI', 'action': '减多',
        'quantity': 339.5, 'direction': 'long', 'profit_target': '0.632', 'stop_loss': '0.546',
        'timestamp': '2025-11-05T10:25:59.155184'
    }
]


def load_config_from_env():
    """从环境变量加载配置"""
    load_dotenv()
    
    # 获取交易模式
    trading_mode = int(os.getenv('BITGET_TRADING_MODE', '0'))
    
    config = {
        # 实盘配置
        'bitget_api_key': os.getenv('BITGET_API_KEY'),
        'bitget_secret_key': os.getenv('BITGET_SECRET_KEY'),
        'bitget_passphrase': os.getenv('BITGET_PASSPHRASE'),
        # 模拟盘配置
        'bitget_demo_api_key': os.getenv('BITGET_DEMO_API_KEY'),
        'bitget_demo_secret_key': os.getenv('BITGET_DEMO_SECRET_KEY'),
        'bitget_demo_passphrase': os.getenv('BITGET_DEMO_PASSPHRASE'),
        # 其他配置
        'bitget_scale_ratio': float(os.getenv('BITGET_SCALE_RATIO', '0.01')),  # 默认 1%
        'bitget_trading_mode': trading_mode,
    }
    
    # 根据交易模式验证配置
    mode = config['bitget_trading_mode']
    
    if mode == 1 or mode == 2:  # 需要实盘配置
        if not all([config['bitget_api_key'], config['bitget_secret_key'], config['bitget_passphrase']]):
            logger.error("❌ 错误: 实盘模式需要配置实盘 API 密钥")
            logger.error("请在 .env 文件中配置以下变量：")
            logger.error("  - BITGET_API_KEY")
            logger.error("  - BITGET_SECRET_KEY")
            logger.error("  - BITGET_PASSPHRASE")
            sys.exit(1)
    
    if mode == 0 or mode == 2:  # 需要模拟盘配置
        if not all([config['bitget_demo_api_key'], config['bitget_demo_secret_key'], config['bitget_demo_passphrase']]):
            logger.error("❌ 错误: 模拟盘模式需要配置模拟盘 API 密钥")
            logger.error("请在 .env 文件中配置以下变量：")
            logger.error("  - BITGET_DEMO_API_KEY")
            logger.error("  - BITGET_DEMO_SECRET_KEY")
            logger.error("  - BITGET_DEMO_PASSPHRASE")
            logger.error("")
            logger.error("💡 提示: 模拟盘 API Key 需要在 Bitget 模拟交易页面单独创建")
            sys.exit(1)
    
    # 显示当前模式
    mode_names = {0: "模拟盘", 1: "实盘", 2: "双盘同步"}
    logger.info(f"🎯 交易模式: {mode_names.get(mode, '未知')} (BITGET_TRADING_MODE={mode})")
    
    return config


def init_trader_from_config(config: dict, scale_ratio: float = 1.0):
    """
    根据配置初始化交易器（单一或多模式）
    
    Args:
        config: 配置字典
        scale_ratio: 缩放比例
        
    Returns:
        交易器实例
    """
    mode = config['bitget_trading_mode']
    
    logger.info("🔧 正在初始化 Bitget 交易器...")
    
    try:
        # 根据模式选择 API Key
        if mode == 0:  # 模拟盘
            logger.info("📌 使用模拟盘 API Key")
            trader = BitgetTraderCCXT(
                api_key=config['bitget_demo_api_key'],
                secret_key=config['bitget_demo_secret_key'],
                passphrase=config['bitget_demo_passphrase'],
                scale_ratio=scale_ratio,
                env_name='模拟盘'
            )
            trader.load_markets()
            trader.test_connection()
            logger.info("✅ 模拟盘交易器初始化成功")
            
        elif mode == 1:  # 实盘
            logger.info("📌 使用实盘 API Key")
            trader = BitgetTraderCCXT(
                api_key=config['bitget_api_key'],
                secret_key=config['bitget_secret_key'],
                passphrase=config['bitget_passphrase'],
                scale_ratio=scale_ratio,
                env_name='实盘'
            )
            trader.load_markets()
            trader.test_connection()
            logger.info("✅ 实盘交易器初始化成功")
            
        elif mode == 2:  # 双盘
            logger.info("📌 使用双盘模式")
            trader = BitgetMultiModeTrader(
                mode=mode,
                live_api_key=config['bitget_api_key'],
                live_secret_key=config['bitget_secret_key'],
                live_passphrase=config['bitget_passphrase'],
                demo_api_key=config['bitget_demo_api_key'],
                demo_secret_key=config['bitget_demo_secret_key'],
                demo_passphrase=config['bitget_demo_passphrase'],
                scale_ratio=scale_ratio
            )
            trader.test_connection()
            logger.info("✅ 双盘交易器初始化成功")
            
        else:
            logger.error(f"❌ 未知的交易模式: {mode}")
            return None
        
        logger.info("")
        return trader
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_test_info(dry_run: bool, trades_to_test: list, config: dict = None):
    """打印测试信息"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🧪 Bitget 交易功能测试")
    logger.info("=" * 80)
    logger.info(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔸 运行模式: {'模拟运行（不实际下单）' if dry_run else '⚠️  实际下单模式'}")
    if config:
        logger.info(f"📊 缩放比例: {config['bitget_scale_ratio']}")
        mode_names = {0: "模拟盘", 1: "实盘", 2: "双盘同步"}
        logger.info(f"🎯 交易模式: {mode_names.get(config['bitget_trading_mode'], '未知')}")
    logger.info(f"📝 测试交易数: {len(trades_to_test)}")
    logger.info("=" * 80)
    logger.info("")


def run_test(dry_run: bool = True, single_trade_index: int = None):
    """
    运行减仓测试
    
    Args:
        dry_run: 是否模拟运行（True=只打印不下单，False=实际下单）
        single_trade_index: 如果指定，只测试指定索引的交易
    """
    # 加载配置
    logger.info("📋 正在加载配置...")
    config = load_config_from_env()
    scale_ratio = config['bitget_scale_ratio']
    
    # 准备测试数据
    if single_trade_index is not None:
        if 0 <= single_trade_index < len(TEST_TRADES):
            trades_to_test = [TEST_TRADES[single_trade_index]]
            logger.info(f"📌 测试单个交易: 索引 {single_trade_index}")
        else:
            logger.error(f"❌ 无效的索引: {single_trade_index}，有效范围: 0-{len(TEST_TRADES)-1}")
            return
    else:
        trades_to_test = TEST_TRADES
        logger.info(f"📌 测试所有交易: 共 {len(trades_to_test)} 个")
    
    # 打印测试信息
    print_test_info(dry_run, trades_to_test, config)
    
    # 等待用户确认（实际下单模式）
    if not dry_run:
        logger.warning("⚠️  警告: 您即将在实盘环境进行交易！")
        logger.warning(f"⚠️  将执行 {len(trades_to_test)} 个减仓操作，使用真实资金！")
        response = input("\n确认继续吗? 输入 'YES' 继续，其他任意键取消: ")
        if response != 'YES':
            logger.info("❌ 测试已取消")
            return
        logger.info("")
    
    # 初始化交易器
    trader = init_trader_from_config(config, scale_ratio=scale_ratio)
    if not trader:
        logger.error("❌ 交易器初始化失败")
        return
    
    # 执行交易
    logger.info("🚀 开始执行交易...")
    logger.info("")
    
    result = trader.execute_trades(trades_to_test, dry_run=dry_run)
    
    # 打印结果
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 测试完成")
    logger.info("=" * 80)
    logger.info(f"✅ 成功: {result.get('success', 0)}")
    logger.info(f"❌ 失败: {result.get('failed', 0)}")
    logger.info("=" * 80)


def test_open_position(dry_run: bool = True):
    """
    测试开仓功能（买入 BTC 并设置止盈止损）
    
    Args:
        dry_run: 是否模拟运行
    """
    # 加载配置
    logger.info("📋 正在加载配置...")
    config = load_config_from_env()
    
    # 测试参数
    symbol = 'BTC/USDT:USDT'
    amount = 0.0001  # 买入 0.0001 BTC
    tp_price = 110000  # 止盈价格
    sl_price = 100000  # 止损价格
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("🧪 测试开仓买入 BTC（含止盈止损）")
    logger.info("=" * 80)
    logger.info(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔸 运行模式: {'模拟运行（不实际下单）' if dry_run else '⚠️  实际下单模式'}")
    logger.info("")
    logger.info(f"📊 交易参数:")
    logger.info(f"   币种: {symbol}")
    logger.info(f"   数量: {amount} BTC")
    logger.info(f"   操作: 市价买入（做多）")
    logger.info(f"   止盈: {tp_price}")
    logger.info(f"   止损: {sl_price}")
    logger.info("=" * 80)
    logger.info("")
    
    # 等待用户确认（实际下单模式）
    if not dry_run:
        logger.warning("⚠️  警告: 您即将在实盘环境进行交易！")
        logger.warning(f"⚠️  将买入 {amount} BTC，使用真实资金！")
        response = input("\n确认继续吗? 输入 'YES' 继续，其他任意键取消: ")
        if response != 'YES':
            logger.info("❌ 测试已取消")
            return
        logger.info("")
    
    # 初始化交易器
    trader = init_trader_from_config(config, scale_ratio=1.0)
    if not trader:
        logger.error("❌ 交易器初始化失败")
        return
    
    # 模拟运行模式
    if dry_run:
        logger.info("🔸 模拟运行模式：将模拟执行以下操作（不实际下单）")
        logger.info("")
        logger.info("操作: 市价买入（做多）")
        logger.info(f"  交易对: {symbol}")
        logger.info(f"  数量: {amount} BTC")
        logger.info(f"  止盈: {tp_price}")
        logger.info(f"  止损: {sl_price}")
        logger.info("")
        logger.info("✅ 模拟运行完成")
        return
    
    # 实际执行
    logger.info("🚀 开始执行实际交易...")
    logger.info("")
    
    try:
        # 步骤 1: 市价买入
        logger.info("📈 步骤 1/3: 市价买入 BTC")
        order = trader.place_order(
            symbol=symbol,
            side='buy',
            order_type='market',
            amount=amount
        )
        
        if not order:
            logger.error("❌ 买入失败")
            return
        
        logger.info(f"✅ 买入成功！订单ID: {order.get('id')}")
        logger.info("")
        
        # 步骤 2: 设置止盈止损
        logger.info("📈 步骤 2/3: 设置止盈止损")
        tp_sl_result = trader.set_take_profit_stop_loss(
            symbol=symbol,
            side='sell',  # 平多仓用 sell
            amount=amount,
            take_profit_price=tp_price,
            stop_loss_price=sl_price
        )
        
        if tp_sl_result.get('take_profit'):
            logger.info("✅ 止盈设置成功")
        if tp_sl_result.get('stop_loss'):
            logger.info("✅ 止损设置成功")
        logger.info("")
        
        # 步骤 3: 查询持仓确认
        logger.info("📈 步骤 3/3: 查询持仓确认")
        positions = trader.get_position(symbol)
        if positions:
            for pos in positions:
                logger.info(f"✅ 持仓确认: {pos.get('side')} {pos.get('contracts')} 张")
        logger.info("")
        
        logger.info("=" * 80)
        logger.info("✅ 开仓测试完成！")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


def test_add_position(dry_run: bool = True):
    """
    测试加仓功能（在已有持仓基础上加仓）
    
    Args:
        dry_run: 是否模拟运行
    """
    # 加载配置
    logger.info("📋 正在加载配置...")
    config = load_config_from_env()
    
    # 测试参数
    symbol = 'BTC/USDT:USDT'
    amount = 0.001  # 加仓 0.001 BTC
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("🧪 测试加仓 BTC")
    logger.info("=" * 80)
    logger.info(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔸 运行模式: {'模拟运行（不实际下单）' if dry_run else '⚠️  实际下单模式'}")
    logger.info("")
    logger.info(f"📊 交易参数:")
    logger.info(f"   币种: {symbol}")
    logger.info(f"   数量: {amount} BTC")
    logger.info(f"   操作: 市价买入（加多仓）")
    logger.info(f"   说明: 在已有持仓基础上增加仓位")
    logger.info("=" * 80)
    logger.info("")
    
    if not dry_run:
        logger.warning("⚠️  警告: 您即将在实盘环境进行交易！")
        logger.warning(f"⚠️  将加仓 {amount} BTC，使用真实资金！")
        response = input("\n确认继续吗? 输入 'YES' 继续，其他任意键取消: ")
        if response != 'YES':
            logger.info("❌ 测试已取消")
            return
        logger.info("")
    
    # 初始化交易器
    trader = init_trader_from_config(config, scale_ratio=1.0)
    if not trader:
        logger.error("❌ 交易器初始化失败")
        return
    
    if dry_run:
        logger.info("🔸 模拟运行模式：将模拟执行以下操作（不实际下单）")
        logger.info("")
        logger.info("操作: 市价买入（加仓）")
        logger.info(f"  交易对: {symbol}")
        logger.info(f"  数量: {amount} BTC")
        logger.info("")
        logger.info("✅ 模拟运行完成")
        return
    
    # 实际执行加仓
    logger.info("🚀 开始执行加仓...")
    order = trader.place_order(
        symbol=symbol,
        side='buy',
        order_type='market',
        amount=amount
    )
    
    if order:
        logger.info(f"✅ 加仓成功！订单ID: {order.get('id')}")
    else:
        logger.error("❌ 加仓失败")


def test_reduce_position(dry_run: bool = True):
    """
    测试减仓功能
    
    Args:
        dry_run: 是否模拟运行
    """
    # 加载配置
    logger.info("📋 正在加载配置...")
    config = load_config_from_env()
    
    # 测试参数
    symbol = 'BTC/USDT:USDT'
    amount = 0.0005  # 减仓 0.0005 BTC
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("🧪 测试减仓 BTC")
    logger.info("=" * 80)
    logger.info(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔸 运行模式: {'模拟运行（不实际下单）' if dry_run else '⚠️  实际下单模式'}")
    logger.info("")
    logger.info(f"📊 交易参数:")
    logger.info(f"   币种: {symbol}")
    logger.info(f"   数量: {amount} BTC")
    logger.info(f"   操作: 市价卖出（减多仓）")
    logger.info(f"   说明: 部分平仓，保留部分持仓")
    logger.info("=" * 80)
    logger.info("")
    
    if not dry_run:
        logger.warning("⚠️  警告: 您即将在实盘环境进行交易！")
        logger.warning(f"⚠️  将减仓 {amount} BTC！")
        response = input("\n确认继续吗? 输入 'YES' 继续，其他任意键取消: ")
        if response != 'YES':
            logger.info("❌ 测试已取消")
            return
        logger.info("")
    
    # 初始化交易器
    trader = init_trader_from_config(config, scale_ratio=1.0)
    if not trader:
        logger.error("❌ 交易器初始化失败")
        return
    
    if dry_run:
        logger.info("🔸 模拟运行模式：将模拟执行以下操作（不实际下单）")
        logger.info("")
        logger.info("操作: 市价卖出（减仓）")
        logger.info(f"  交易对: {symbol}")
        logger.info(f"  数量: {amount} BTC")
        logger.info("")
        logger.info("✅ 模拟运行完成")
        return
    
    # 实际执行减仓
    logger.info("🚀 开始执行减仓...")
    order = trader.place_order(
        symbol=symbol,
        side='sell',
        order_type='market',
        amount=amount,
        params={'reduceOnly': True}
    )
    
    if order:
        logger.info(f"✅ 减仓成功！订单ID: {order.get('id')}")
    else:
        logger.error("❌ 减仓失败")


def test_close_position(dry_run: bool = True):
    """
    测试平仓功能（完全平掉所有持仓）
    
    Args:
        dry_run: 是否模拟运行
    """
    # 加载配置
    logger.info("📋 正在加载配置...")
    config = load_config_from_env()
    
    # 测试参数
    symbol = 'BTC/USDT:USDT'
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("🧪 测试平仓 BTC")
    logger.info("=" * 80)
    logger.info(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔸 运行模式: {'模拟运行（不实际下单）' if dry_run else '⚠️  实际下单模式'}")
    logger.info("")
    logger.info(f"📊 交易参数:")
    logger.info(f"   币种: {symbol}")
    logger.info(f"   操作: 市价平仓（平多仓）")
    logger.info(f"   说明: 完全平掉所有持仓")
    logger.info("=" * 80)
    logger.info("")
    
    if not dry_run:
        logger.warning("⚠️  警告: 您即将在实盘环境进行交易！")
        logger.warning(f"⚠️  将完全平仓 {symbol} 所有持仓！")
        response = input("\n确认继续吗? 输入 'YES' 继续，其他任意键取消: ")
        if response != 'YES':
            logger.info("❌ 测试已取消")
            return
        logger.info("")
    
    # 初始化交易器
    trader = init_trader_from_config(config, scale_ratio=1.0)
    if not trader:
        logger.error("❌ 交易器初始化失败")
        return
    
    if dry_run:
        logger.info("🔸 模拟运行模式：将模拟执行以下操作（不实际下单）")
        logger.info("")
        logger.info("操作: 查询持仓并完全平仓")
        logger.info(f"  交易对: {symbol}")
        logger.info("")
        logger.info("✅ 模拟运行完成")
        return
    
    # 实际执行平仓
    logger.info("🚀 开始执行平仓...")
    success = trader.close_all_positions(symbol)
    
    if success:
        logger.info("✅ 平仓完成")
    else:
        logger.error("❌ 平仓失败或无持仓")


def test_full_flow(dry_run: bool = True):
    """
    测试完整流程：开仓 -> 加仓 -> 减仓 -> 平仓
    
    Args:
        dry_run: 是否模拟运行
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("🧪 Bitget 完整流程测试")
    logger.info("=" * 80)
    logger.info(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔸 运行模式: {'模拟运行' if dry_run else '⚠️  实际下单'}")
    logger.info("")
    logger.info("📝 测试流程:")
    logger.info("  1️⃣  开仓: 买入 0.0001 BTC + 止盈止损")
    logger.info("  2️⃣  加仓: 加仓 0.001 BTC")
    logger.info("  3️⃣  减仓: 减仓 0.0005 BTC")
    logger.info("  4️⃣  平仓: 完全平仓")
    logger.info("=" * 80)
    logger.info("")
    
    if not dry_run:
        logger.warning("⚠️  警告: 您即将执行完整交易流程！")
        response = input("\n确认继续吗? 输入 'YES' 继续，其他任意键取消: ")
        if response != 'YES':
            logger.info("❌ 测试已取消")
            return
        logger.info("")
    
    # 执行各步骤
    logger.info("=" * 80)
    logger.info("1️⃣  开始测试：开仓")
    logger.info("=" * 80)
    test_open_position(dry_run)
    
    if not dry_run:
        input("\n按 Enter 继续下一步（加仓）...")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("2️⃣  开始测试：加仓")
    logger.info("=" * 80)
    test_add_position(dry_run)
    
    if not dry_run:
        input("\n按 Enter 继续下一步（减仓）...")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("3️⃣  开始测试：减仓")
    logger.info("=" * 80)
    test_reduce_position(dry_run)
    
    if not dry_run:
        input("\n按 Enter 继续下一步（平仓）...")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("4️⃣  开始测试：平仓")
    logger.info("=" * 80)
    test_close_position(dry_run)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ 完整流程测试完成！")
    logger.info("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Bitget 交易功能测试脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # ========== 减仓测试（使用日志真实数据）==========
  python test_bitget_trading.py                  # 模拟所有减仓
  python test_bitget_trading.py --single 0       # 模拟单个减仓
  python test_bitget_trading.py --real --single 0  # 实际单个减仓

  # ========== 单项功能测试 ==========
  python test_bitget_trading.py --open           # 模拟开仓
  python test_bitget_trading.py --add            # 模拟加仓
  python test_bitget_trading.py --reduce         # 模拟减仓
  python test_bitget_trading.py --close          # 模拟平仓

  # ========== 实际下单（谨慎！）==========
  python test_bitget_trading.py --real --open    # 实际开仓
  python test_bitget_trading.py --real --add     # 实际加仓
  python test_bitget_trading.py --real --reduce  # 实际减仓
  python test_bitget_trading.py --real --close   # 实际平仓

  # ========== 完整流程测试 ==========
  python test_bitget_trading.py --flow           # 模拟完整流程
  python test_bitget_trading.py --real --flow    # 实际完整流程
        '''
    )
    
    parser.add_argument('--real', action='store_true', help='实际下单（默认为模拟运行）')
    parser.add_argument('--single', type=int, metavar='INDEX', help='只测试指定索引的交易')
    parser.add_argument('--open', action='store_true', help='测试开仓功能')
    parser.add_argument('--add', action='store_true', help='测试加仓功能')
    parser.add_argument('--reduce', action='store_true', help='测试减仓功能')
    parser.add_argument('--close', action='store_true', help='测试平仓功能')
    parser.add_argument('--flow', action='store_true', help='测试完整流程')
    
    args = parser.parse_args()
    dry_run = not args.real
    
    if args.flow:
        test_full_flow(dry_run=dry_run)
    elif args.open:
        test_open_position(dry_run=dry_run)
    elif args.add:
        test_add_position(dry_run=dry_run)
    elif args.reduce:
        test_reduce_position(dry_run=dry_run)
    elif args.close:
        test_close_position(dry_run=dry_run)
    else:
        run_test(dry_run=dry_run, single_trade_index=args.single)


if __name__ == '__main__':
    main()

