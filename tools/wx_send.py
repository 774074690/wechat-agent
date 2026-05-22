import uiautomation as auto
import sys, time

def send_wechat_msg(contact, message):
    auto.uiautomation.TIME_OUT_SECOND = 3

    root = auto.GetRootControl()
    wx = None
    for w in root.GetChildren():
        if w.Name == '微信':
            wx = w
            break
    if not wx:
        print('ERROR: 微信窗口未打开')
        return False
    print(f'[1] 微信已找到')

    try:
        # 如果窗口是缩小的，先还原
        try:
            wx.ShowWindow(9)  # SW_RESTORE
        except:
            pass
        time.sleep(0.3)
        wx.SwitchToThisWindow()
        print('[2] 窗口已激活')
    except Exception as e:
        print(f'[2] 激活失败: {e}')
    time.sleep(0.5)

    # 搜索联系人（粘贴方式避免中文输入法问题）
    print('[3] Ctrl+F 搜索...')
    auto.SendKeys('{Ctrl}f', waitTime=0.3)
    time.sleep(0.5)
    auto.SendKeys('{Ctrl}a', waitTime=0.2)
    time.sleep(0.2)
    auto.SetClipboardText(contact)
    time.sleep(0.2)
    auto.SendKeys('{Ctrl}v', waitTime=0.3)
    time.sleep(0.8)
    auto.SendKeys('{Enter}', waitTime=0.3)
    time.sleep(1.0)

    # 点一下输入框区域（窗口底部中央）确保聚焦
    rect = wx.BoundingRectangle
    x = (rect.left + rect.right) // 2
    y = rect.bottom - 80
    print(f'[4] 点击输入框 ({x}, {y})')
    auto.Click(x, y)
    time.sleep(0.5)

    # 粘贴消息
    print(f'[5] 发送: "{message}"')
    auto.SetClipboardText(message)
    time.sleep(0.2)
    auto.SendKeys('{Ctrl}v', waitTime=0.3)
    time.sleep(0.3)

    auto.SendKeys('{Enter}', waitTime=0.3)
    time.sleep(0.5)

    print('[6] 完成')
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: python wx_send.py "联系人" "消息内容"')
        sys.exit(1)
    contact = sys.argv[1]
    message = sys.argv[2]
    ok = send_wechat_msg(contact, message)
    sys.exit(0 if ok else 1)
