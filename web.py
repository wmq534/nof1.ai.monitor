import json
import os
import time
from flask import Flask, render_template_string, abort, request, url_for, jsonify, redirect
from config_manager import ConfigManager
from dotenv import load_dotenv


app = Flask(__name__)

# 加载环境变量
load_dotenv()

# 初始化配置管理器
config_manager = ConfigManager()


def load_last_json():
    last_path = os.path.join(os.path.dirname(__file__), 'last.json')
    if not os.path.exists(last_path):
        abort(404, description='last.json not found')
    with open(last_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_ts(ts):
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(ts)))
    except Exception:
        return '-'


@app.route('/')
def index():
    data = load_last_json()
    # Expect data['positions'] to be a list of model snapshots
    models = data.get('positions', [])
    
    # Calculate unrealized and total PnL for each model
    for m in models:
        realized_pnl = m.get('realized_pnl', 0.0) or 0.0
        unrealized_pnl = 0.0
        positions = m.get('positions', {})
        for pos in positions.values():
            unrealized_pnl += (pos.get('unrealized_pnl', 0.0) or 0.0)
        m['unrealized_pnl'] = unrealized_pnl
        m['total_pnl'] = realized_pnl + unrealized_pnl
    
    # Sort by realized_pnl descending
    models = sorted(models, key=lambda m: (m.get('realized_pnl') or 0.0), reverse=True)

    # Extract a sorted list of all symbols observed across models for header consistency
    all_symbols = set()
    for m in models:
        for sym in (m.get('positions') or {}).keys():
            all_symbols.add(sym)
    sorted_symbols = sorted(all_symbols)

    # i18n strings
    lang = request.args.get('lang', 'zh')
    is_en = (lang == 'en')
    t = {
        'title': 'Alpha Arena 持仓监控' if not is_en else 'Alpha Arena Positions Monitor',
        'data_time': '数据时间' if not is_en else 'Data Time',
        'auto_refresh': '自动每15秒刷新' if not is_en else 'Auto refresh every 15s',
        'delay': '提示：与官网数据存在约1分钟延时' if not is_en else 'Note: ~1 minute delay vs. official site',
        'model': '模型' if not is_en else 'Model',
        'rpnl': '已实现盈亏' if not is_en else 'Realized PnL',
        'urpnl': '未实现盈亏' if not is_en else 'Unrealized PnL',
        'tpnl': '总盈亏' if not is_en else 'Total PnL',
        'pair': '合约对' if not is_en else 'Pair',
        'qty': '数量' if not is_en else 'Qty',
        'lev': '杠杆' if not is_en else 'Lev',
        'entry': '开仓价' if not is_en else 'Entry',
        'price': '当前价' if not is_en else 'Price',
        'margin': '保证金' if not is_en else 'Margin',
        'upnl': '浮动盈亏' if not is_en else 'U-PnL',
        'cpnl': '平仓盈亏' if not is_en else 'C-PnL',
        'tp': '止盈' if not is_en else 'TP',
        'sl': '止损' if not is_en else 'SL',
        'entry_time': '进入时间' if not is_en else 'Entry Time',
        'file': '文件' if not is_en else 'File',
        'size': '大小' if not is_en else 'Size',
        'toggle': 'English' if not is_en else '中文',
        'contact': '联系方式' if not is_en else 'Contact',
        'nof1': 'nof1.ai' if not is_en else 'nof1.ai',
        'wechat_mp': '公众号:远见拾贝' if not is_en else 'WeChat MP',
        'x': 'X' if is_en else 'X',
        'github': 'Github' if not is_en else 'GitHub',
        'site': '网站' if not is_en else 'Site',
        'disclaimer': '声明：本网站仅供学习和研究使用，不构成投资建议。所有交易决策由用户自行承担风险。作者对任何投资损失不承担责任。如果您发现本网站内容侵犯了您的权益，请联系我们立即处理。' if not is_en else 'Disclaimer: This website is for learning and research only, and does not constitute investment advice. All trading decisions are at your own risk. The author is not responsible for any investment losses. If you find any infringement, please contact us immediately.',
    }

    # HTML template with auto refresh every 15 seconds
    template = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>持仓监控</title>
  <meta http-equiv="refresh" content="15">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 20px; }
    h1 { font-size: 20px; margin: 0 0 16px; }
    .meta { color: #666; font-size: 12px; margin-bottom: 16px; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 28px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
    th { background: #f7f7f7; position: sticky; top: 0; }
    td.sym, th.sym { text-align: left; }
    .pos { color: #111; }
    .neg { color: #b00020; }
    .zero { color: #666; }
    .model { font-size: 16px; margin: 24px 0 8px; }
    .topbar { position: fixed; right: 20px; top: 12px; font-size: 12px; color: #555; }
    .topbar a { color: #0a58ca; text-decoration: none; margin-left: 10px; }
    .spacer { height: 28px; }
  </style>
  <script>
    // In case meta refresh is blocked, fallback to JS reload
    setTimeout(function(){ window.location.reload(); }, 15000);
  </script>
  </head>
<body>
  <div class="topbar">
    {{ t['contact'] }}:
    <a href="https://nof1.ai" target="_blank" rel="noopener">{{ t['nof1'] }}</a>
    <a href="https://www.insightpearl.com/" target="_blank" rel="noopener">{{ t['site'] }}</a>
    <a href="https://x.com/okay456okay" target="_blank" rel="noopener">{{ t['x'] }}</a>
    <a href="https://github.com/okay456okay/nof1.ai.monitor" target="_blank" rel="noopener">{{ t['github'] }}</a>
    <a href="https://www.insightpearl.com/" target="_blank" rel="noopener">{{ t['wechat_mp'] }}</a>
    | <a href="{{ url_for('settings', lang=lang) }}">⚙️ {{ 'Bitget设置' if not is_en else 'Bitget Settings' }}</a>
    | <a href="{{ url_for('index', lang='en' if not is_en else 'zh') }}">{{ t['toggle'] }}</a>
  </div>
  <div class="spacer"></div>
  <h1>{{ t['title'] }}</h1>
  <div class="meta">
    {{ t['data_time'] }}：{{ data.get('fetch_time') or data.get('timestamp') }} &nbsp;|&nbsp; {{ t['auto_refresh'] }} &nbsp;|&nbsp; {{ t['delay'] }}
  </div>

  {% for m in models %}
    <div class="model">{{ t['model'] }}：<strong><a href="https://nof1.ai/models/{{ m.get('id') }}" target="_blank" rel="noopener">{{ m.get('id') }}</a></strong> &nbsp; {{ t['rpnl'] }}：{{ '%.2f' % (m.get('realized_pnl', 0.0) or 0.0) }}，{{ t['urpnl'] }}：{{ '%.2f' % (m.get('unrealized_pnl', 0.0) or 0.0) }}，{{ t['tpnl'] }}：{{ '%.2f' % (m.get('total_pnl', 0.0) or 0.0) }}</div>
    <table>
      <thead>
        <tr>
          <th class="sym">{{ t['pair'] }}</th>
          <th>{{ t['qty'] }}</th>
          <th>{{ t['lev'] }}</th>
          <th>{{ t['entry'] }}</th>
          <th>{{ t['price'] }}</th>
          <th>{{ t['margin'] }}</th>
          <th>{{ t['upnl'] }}</th>
          <th>{{ t['cpnl'] }}</th>
          <th>{{ t['tp'] }}</th>
          <th>{{ t['sl'] }}</th>
          <th>{{ t['entry_time'] }}</th>
        </tr>
      </thead>
      <tbody>
        {% set pos_map = m.get('positions') or {} %}
        {% for sym in sorted_symbols %}
          {% set p = pos_map.get(sym) %}
          {% if p %}
            {% set upnl = p.get('unrealized_pnl', 0.0) or 0.0 %}
            {% set cpnl = p.get('closed_pnl', 0.0) or 0.0 %}
            <tr>
              <td class="sym">{{ sym }}</td>
              <td>{{ p.get('quantity') }}</td>
              <td>{{ p.get('leverage') }}</td>
              <td>{{ '%.6g' % (p.get('entry_price') or 0) }}</td>
              <td>{{ '%.6g' % (p.get('current_price') or 0) }}</td>
              <td>{{ '%.2f' % (p.get('margin', 0.0) or 0.0) }}</td>
              <td class="{{ 'pos' if upnl>0 else ('neg' if upnl<0 else 'zero') }}">{{ '%.2f' % upnl }}</td>
              <td class="{{ 'pos' if cpnl>0 else ('neg' if cpnl<0 else 'zero') }}">{{ '%.2f' % cpnl }}</td>
              <td>{% if p.get('exit_plan') %}{{ p['exit_plan'].get('profit_target') }}{% endif %}</td>
              <td>{% if p.get('exit_plan') %}{{ p['exit_plan'].get('stop_loss') }}{% endif %}</td>
              <td>{% set et = p.get('entry_time') %}{{ format_ts(et) if et else '-' }}</td>
            </tr>
          {% else %}
            <tr>
              <td class="sym">{{ sym }}</td>
              <td colspan="11" style="text-align:center;color:#999">—</td>
            </tr>
          {% endif %}
        {% endfor %}
      </tbody>
    </table>
  {% endfor %}

  <div class="meta">{{ t['file'] }}：last.json &nbsp; {{ t['size'] }}：{{ (json_str|length) }} {{ 'bytes' if is_en else '字节' }}</div>

  <div style="margin-top: 40px; padding: 20px; background: #f9f9f9; border-radius: 4px; font-size: 12px; line-height: 1.8; color: #666;">
    {{ t['disclaimer'] }}
  </div>
</body>
</html>
"""

    json_str = json.dumps(data, ensure_ascii=False)
    return render_template_string(
        template,
        data=data,
        models=models,
        sorted_symbols=sorted_symbols,
        json_str=json_str,
        format_ts=format_ts,
        t=t,
        is_en=is_en,
    )


@app.route('/settings')
def settings():
    """配置页面"""
    config = config_manager.load_config()
    
    # 获取可用的模型列表（从 last.json）
    available_models = []
    try:
        data = load_last_json()
        models = data.get('positions', [])
        available_models = [m.get('id') for m in models if m.get('id')]
    except Exception:
        pass
    
    # 获取 Bitget API 配置状态
    api_configured = bool(os.getenv('BITGET_API_KEY') and 
                         os.getenv('BITGET_SECRET_KEY') and 
                         os.getenv('BITGET_PASSPHRASE'))
    
    lang = request.args.get('lang', 'zh')
    is_en = (lang == 'en')
    
    t = {
        'title': 'Bitget 跟单设置' if not is_en else 'Bitget Follow Settings',
        'enabled': '启用自动跟单' if not is_en else 'Enable Auto Follow',
        'disabled': '已禁用' if not is_en else 'Disabled',
        'scale_ratio': '缩放比例' if not is_en else 'Scale Ratio',
        'scale_ratio_desc': '将原始交易量按此比例缩放（如 0.1 表示缩小到 10%）' if not is_en else 'Scale original trade size by this ratio (e.g., 0.1 means 10%)',
        'whitelist': '白名单模型' if not is_en else 'Whitelist Models',
        'whitelist_desc': '只跟随选中的模型交易，留空则跟随所有模型' if not is_en else 'Only follow selected models, leave empty to follow all',
        'max_amount': '单笔最大金额 (USDT)' if not is_en else 'Max Single Trade (USDT)',
        'dry_run': '模拟运行模式' if not is_en else 'Dry Run Mode',
        'dry_run_desc': '只记录日志不实际下单' if not is_en else 'Log only, no actual orders',
        'notification': '交易后发送通知' if not is_en else 'Notify After Trade',
        'api_status': 'API 配置状态' if not is_en else 'API Status',
        'api_ok': '已配置' if not is_en else 'Configured',
        'api_not': '未配置' if not is_en else 'Not Configured',
        'api_hint': '请在 .env 文件中配置 BITGET_API_KEY, BITGET_SECRET_KEY, BITGET_PASSPHRASE' if not is_en else 'Please configure BITGET_API_KEY, BITGET_SECRET_KEY, BITGET_PASSPHRASE in .env file',
        'save': '保存配置' if not is_en else 'Save',
        'back': '返回持仓页面' if not is_en else 'Back to Positions',
        'risk_warning': '⚠️ 风险提示：所有仓位都会强制设置止盈止损，若源交易缺少止盈止损将拒绝跟单' if not is_en else '⚠️ Risk Warning: All positions require stop-loss and take-profit. Trades without SL/TP will be rejected',
    }
    
    template = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ t['title'] }}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 20px; max-width: 800px; }
    h1 { font-size: 24px; margin: 0 0 20px; }
    .form-group { margin-bottom: 20px; }
    label { display: block; font-weight: 600; margin-bottom: 5px; }
    .hint { font-size: 12px; color: #666; margin-top: 3px; }
    input[type="number"], input[type="text"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
    .checkbox-group { padding: 10px; border: 1px solid #ddd; border-radius: 4px; max-height: 200px; overflow-y: auto; }
    .checkbox-item { margin: 5px 0; }
    .checkbox-item input { margin-right: 8px; }
    .toggle { position: relative; display: inline-block; width: 50px; height: 24px; }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 24px; }
    .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
    input:checked + .slider { background-color: #2196F3; }
    input:checked + .slider:before { transform: translateX(26px); }
    .btn { padding: 10px 20px; background: #0a58ca; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 10px; }
    .btn:hover { background: #084298; }
    .btn-secondary { background: #6c757d; }
    .btn-secondary:hover { background: #5c636a; }
    .status { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
    .status-ok { background: #d1e7dd; color: #0f5132; }
    .status-error { background: #f8d7da; color: #842029; }
    .alert { padding: 15px; margin: 20px 0; border-radius: 4px; background: #fff3cd; border: 1px solid #ffc107; color: #664d03; }
    .success-msg { display: none; padding: 15px; margin: 20px 0; border-radius: 4px; background: #d1e7dd; border: 1px solid #0f5132; color: #0f5132; }
  </style>
</head>
<body>
  <h1>{{ t['title'] }}</h1>
  
  <div class="alert">
    {{ t['risk_warning'] }}
  </div>
  
  <div id="successMsg" class="success-msg"></div>
  
  <form id="settingsForm" onsubmit="return saveSettings(event)">
    <div class="form-group">
      <label>
        {{ t['enabled'] }}
        <label class="toggle" style="float: right;">
          <input type="checkbox" name="enabled" id="enabled" {{ 'checked' if config.get('enabled') else '' }}>
          <span class="slider"></span>
        </label>
      </label>
    </div>
    
    <div class="form-group">
      <label>{{ t['api_status'] }}</label>
      <span class="status {{ 'status-ok' if api_configured else 'status-error' }}">
        {{ t['api_ok'] if api_configured else t['api_not'] }}
      </span>
      {% if not api_configured %}
      <div class="hint">{{ t['api_hint'] }}</div>
      {% endif %}
    </div>
    
    <div class="form-group">
      <label for="scale_ratio">{{ t['scale_ratio'] }}</label>
      <input type="number" id="scale_ratio" name="scale_ratio" min="0.001" max="1" step="0.001" value="{{ config.get('scale_ratio', 0.1) }}" required>
      <div class="hint">{{ t['scale_ratio_desc'] }}</div>
    </div>
    
    <div class="form-group">
      <label for="max_amount">{{ t['max_amount'] }}</label>
      <input type="number" id="max_amount" name="max_single_trade_amount" min="1" step="1" value="{{ config.get('max_single_trade_amount', 1000) }}" required>
    </div>
    
    <div class="form-group">
      <label>{{ t['whitelist'] }}</label>
      <div class="checkbox-group">
        {% if available_models %}
          {% for model in available_models %}
          <div class="checkbox-item">
            <input type="checkbox" name="whitelist_models" value="{{ model }}" id="model_{{ loop.index }}" 
              {{ 'checked' if model in config.get('whitelist_models', []) else '' }}>
            <label for="model_{{ loop.index }}" style="display: inline; font-weight: normal;">{{ model }}</label>
          </div>
          {% endfor %}
        {% else %}
          <div class="hint">暂无可用模型</div>
        {% endif %}
      </div>
      <div class="hint">{{ t['whitelist_desc'] }}</div>
    </div>
    
    <div class="form-group">
      <label>
        {{ t['dry_run'] }}
        <label class="toggle" style="float: right;">
          <input type="checkbox" name="dry_run" id="dry_run" {{ 'checked' if config.get('dry_run') else '' }}>
          <span class="slider"></span>
        </label>
      </label>
      <div class="hint">{{ t['dry_run_desc'] }}</div>
    </div>
    
    <div class="form-group">
      <label>
        {{ t['notification'] }}
        <label class="toggle" style="float: right;">
          <input type="checkbox" name="notification_on_trade" id="notification_on_trade" {{ 'checked' if config.get('notification_on_trade', True) else '' }}>
          <span class="slider"></span>
        </label>
      </label>
    </div>
    
    <div class="form-group">
      <button type="submit" class="btn">{{ t['save'] }}</button>
      <a href="{{ url_for('index', lang=lang) }}" class="btn btn-secondary">{{ t['back'] }}</a>
    </div>
  </form>
  
  <script>
    function saveSettings(event) {
      event.preventDefault();
      
      const form = document.getElementById('settingsForm');
      const formData = new FormData(form);
      
      // 构建配置对象
      const config = {
        enabled: formData.get('enabled') === 'on',
        scale_ratio: parseFloat(formData.get('scale_ratio')),
        max_single_trade_amount: parseFloat(formData.get('max_single_trade_amount')),
        dry_run: formData.get('dry_run') === 'on',
        notification_on_trade: formData.get('notification_on_trade') === 'on',
        whitelist_models: formData.getAll('whitelist_models')
      };
      
      // 发送 POST 请求
      fetch('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          const msg = document.getElementById('successMsg');
          msg.textContent = '✅ 配置保存成功！';
          msg.style.display = 'block';
          setTimeout(() => { msg.style.display = 'none'; }, 3000);
        } else {
          alert('保存失败: ' + (data.error || '未知错误'));
        }
      })
      .catch(error => {
        alert('保存失败: ' + error);
      });
      
      return false;
    }
  </script>
</body>
</html>
"""
    
    return render_template_string(
        template,
        config=config,
        available_models=available_models,
        api_configured=api_configured,
        t=t,
        is_en=is_en,
        lang=lang
    )


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """配置 API 接口"""
    if request.method == 'GET':
        # 获取配置
        config = config_manager.load_config()
        return jsonify({
            'success': True,
            'config': config
        })
    
    elif request.method == 'POST':
        # 更新配置
        try:
            new_config = request.get_json()
            if config_manager.save_config(new_config):
                return jsonify({
                    'success': True,
                    'message': '配置已保存'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '保存配置失败'
                }), 500
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


if __name__ == '__main__':
    # Allow host binding via env var if needed
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5010'))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host=host, port=port, debug=debug)
