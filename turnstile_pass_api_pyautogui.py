from flask import Flask, request, jsonify
import requests
from DrissionPage import Chromium, ChromiumOptions
import time
import os
import random
import pyautogui
from pyvirtualdisplay import Display
import atexit

app = Flask(__name__)
    
def initialize_browser():
    co = ChromiumOptions()
    co.auto_port()

    # 从环境变量获取浏览器路径，默认值为常见路径
    browser_path = os.getenv('BROWSER_PATH', '/usr/bin/google-chrome')
    co.set_browser_path(browser_path)

    co.set_argument('--no-sandbox')
    co.incognito(on_off=True)
    co.set_argument('--window-size=800,600')

    browser = Chromium(addr_or_opts=co)
    tab = browser.latest_tab
    tab.set.load_mode.eager()
    return browser, tab

def get_TurnstileToken(website, sitekey, tab,max_retries=3):
    script_txt = f"""
            (function(){{
                document.body.innerHTML='';
                const sitekey='{sitekey}';
                var container=document.createElement('div');
                container.id='turnstile-test-container';
                document.body.appendChild(container);
                var script=document.createElement('script');
                script.src='https://challenges.cloudflare.com/turnstile/v0/api.js';
                script.async=true;
                script.defer=true;
                document.head.appendChild(script);
                script.onload=function(){{
                    console.log('Turnstile脚本已加载。');
                    window.turnstile.render(container,{{
                        sitekey: sitekey,
                        callback: function(token){{
                            console.log('Turnstile Token:',token);
                            document.cookie = "TurnstileToken=" + token + "; max-age=3600; path=/";
                        }},
                        'error-callback': function(error){{
                            console.error('Turnstile Error:',error);
                        }},
                        'expired-callback': function(){{
                            console.warn('Turnstile Token已过期。');
                        }}
                    }});
                    console.log('Turnstile小部件已渲染。');
                }};
                script.onerror=function(){{
                    console.error('无法加载Turnstile脚本。');
                }};
                console.log('Turnstile iframe 正在加载，等待用户完成验证...');
            }})();
            """
    for attempt in range(1, max_retries + 1):
        try:
            tab.get(website)
            tab.run_js_loaded(script_txt)
            # 获取并操作元素
            container_ele = tab.ele('@id:turnstile-test-container')
            div_elements = container_ele.eles('tag:div')
            if len(div_elements) < 1:
                raise Exception("未找到足够的div元素。")

            sr_ele = div_elements[0].shadow_root
            sr_ele.get_frame(1)
            try:
                captcha_location = None
                start_time = time.time()
                while time.time() - start_time < 10:  # 最多等待10秒
                    try:
                        captcha_location = pyautogui.locateOnScreen('checkboxXvfb.png', confidence=0.5)
                    except:
                        pass
                    if captcha_location:
                        break
                    time.sleep(0.5)
                if captcha_location:
                    if hasattr(captcha_location, 'left'):
                        x = captcha_location.left + captcha_location.width // 2
                        y = captcha_location.top + captcha_location.height // 2
                    else:
                        x = captcha_location[0] + captcha_location[2] // 2
                        y = captcha_location[1] + captcha_location[3] // 2

                    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))  # 增加随机性
                    time.sleep(0.5)
                    pyautogui.click(clicks=1, interval=0.1, _pause=False)
                    tab.wait(1)  # 点击后等待
            except Exception as e:
                # 如果复选框不存在，则记录信息并继续等待
                print(f"第{attempt}次尝试：未找到复选框，继续等待 'TurnstileToken'")
            # 等待token
            for wait_attempt in range(1, 11):
                cookies = tab.cookies().as_dict()
                if 'TurnstileToken' in cookies:
                    print(f"成功获取 'TurnstileToken'：{cookies['TurnstileToken']}")
                    return cookies['TurnstileToken']
                time.sleep(1)  # 等待1秒后重试
            # 如果等待后仍未找到 TurnstileToken
            print(f"第{attempt}次尝试：未找到 'TurnstileToken'。")
        except Exception as e:
            print(f"第{attempt}次尝试：发生异常 - {e}")
    # 达到最大重试次数后仍未成功
    return None

@app.route('/get_TurnstileToken', methods=['POST'])
def fetch_TurnstileToken():
    data = request.get_json()

    if not data:
        return jsonify({"error": "未提供JSON负载。"}), 400

    website = data.get('website')
    sitekey = data.get('sitekey')
    browser = None

    if not website:
        return jsonify({"error": "缺少 'website' 参数。"}), 400

    if not sitekey:
        return jsonify({"error": "缺少 'sitekey' 参数。"}), 400
    try:
        browser, tab = initialize_browser()
        TurnstileToken = get_TurnstileToken(website, sitekey,tab)

        if TurnstileToken:
            response = {
                "website": website,
                "sitekey": sitekey,
                "TurnstileToken": TurnstileToken
            }
            return jsonify(response), 200
        else:
            return jsonify({"error": "未能获取到 'TurnstileToken'。"}), 500

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        return jsonify({"error": f"发生未预期的错误: {e}"}), 500
    finally:
        if browser:
            browser.quit()


@app.route('/', methods=['GET'])
def test():
    response = {"message": "turnstile_pass is running."}

    # 从环境变量中获取是否返回公共IP的配置
    show_ip = os.getenv('SHOW_IP', 'false').lower() == 'true'

    if show_ip:
        try:
            # 发送请求到 api.ipify.org 获取公共IP
            ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
            if ip_response.status_code == 200:
                public_ip = ip_response.json().get('ip')
                response["public_ip"] = public_ip
            else:
                response["public_ip"] = f"无法获取IP，状态码: {ip_response.status_code}"
        except Exception as e:
            response["public_ip"] = f"无法获取IP: {e}"

    return jsonify(response), 200


if __name__ == '__main__':
    display = None
    if DOCKER_MODE:
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        def cleanup_display():
            if display:
                display.stop()
        atexit.register(cleanup_display)
    app.run(host='0.0.0.0', port=5000)
