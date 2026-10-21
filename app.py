import os
import sys  # <--- 【新增】用于处理 EXE 打包后的路径
import cv2
import mss
import numpy as np
from pynput import keyboard
import time
import ctypes
import random
import string
import threading

# 解决 Windows 高 DPI 缩放下的坐标偏差
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 【核心修改】获取正确的运行路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的 EXE 运行，获取 EXE 所在的文件夹
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 如果是 Python 源码运行，获取 py 文件所在的文件夹
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCALES = np.arange(0.6, 1.61, 0.1)
THRESHOLD = 0.70

# ================= 真实英文单词库 =================
ENGLISH_WORDS = [
    "the", "of", "and", "a", "to", "in", "is", "you", "that", "it", "he", "was", "for", "on", "are", "as", "with", "his", "they", "I",
    "at", "be", "this", "have", "from", "or", "one", "had", "by", "word", "but", "not", "what", "all", "were", "we", "when", "your", "can", "said",
    "there", "use", "an", "each", "which", "she", "do", "how", "their", "if", "will", "up", "other", "about", "out", "many", "then", "them", "these", "so",
    "some", "her", "would", "make", "like", "him", "into", "time", "has", "look", "two", "more", "write", "go", "see", "number", "no", "way", "could", "people",
    "my", "than", "first", "water", "been", "call", "who", "oil", "its", "now", "find", "long", "down", "day", "did", "get", "come", "made", "may", "part",
    "book", "story", "novel", "author", "writer", "reader", "page", "print", "paper", "cover", "title", "chapter", "publish", "publisher", "publishing",
    "fiction", "nonfiction", "literature", "classic", "modern", "famous", "popular", "best", "great", "good", "new", "old", "young", "happy", "sad",
    "dark", "light", "night", "morning", "evening", "summer", "winter", "spring", "autumn", "rain", "snow", "wind", "sun", "moon", "star", "sky",
    "sea", "ocean", "river", "lake", "mountain", "forest", "tree", "flower", "grass", "animal", "bird", "fish", "dog", "cat", "horse", "lion",
    "tiger", "bear", "wolf", "fox", "rabbit", "mouse", "house", "home", "room", "door", "window", "table", "chair", "bed", "kitchen", "garden",
    "city", "town", "village", "road", "street", "car", "train", "plane", "boat", "ship", "school", "teacher", "student", "friend", "family",
    "mother", "father", "brother", "sister", "child", "man", "woman", "boy", "girl", "king", "queen", "prince", "princess", "war", "peace",
    "love", "life", "death", "history", "future", "past", "present", "music", "art", "science", "math", "language", "english", "world", "country",
    "nature", "beauty", "truth", "power", "mind", "heart", "soul", "body", "health", "food", "water", "fire", "earth", "air", "stone", "metal"
]

def generate_real_words(target_length):
    result = ""
    while len(result) < target_length:
        word = random.choice(ENGLISH_WORDS)
        if len(result) + len(word) + 1 <= target_length:
            result += word + " "
        else:
            if len(result) + len(word) == target_length:
                result += word
            break
    if len(result) < target_length:
        padding = target_length - len(result)
        result += ''.join(random.choices(string.ascii_letters, k=padding))
    return result[:target_length]

# 生成完整英文句子（支持自定义单词数量，强制保证单词间只有一个空格）
def generate_long_sentence(word_count=None):
    if word_count is None:
        word_count = random.randint(11, 15) 
    words = [random.choice(ENGLISH_WORDS) for _ in range(word_count)]
    sentence = " ".join(words) 
    return sentence.capitalize() + "."

# =================================================

# 1. 通用找图函数
def find_template(image_name):
    image_path = os.path.join(BASE_DIR, "Images", image_name)
    template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    if template is None:
        print(f"[!] 错误：找不到图片：{image_path}")
        return None, 0, 0, 0, 0, 0

    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)

        best_score = -1
        best_pos = None
        best_h = 0 
        best_w = 0
        best_loc_x = 0
        best_loc_y = 0

        screen_h, screen_w = screen_gray.shape[:2]
        temp_h, temp_w = template.shape[:2]

        for scale in SCALES:
            w = int(temp_w * scale)
            h = int(temp_h * scale)

            if w < 10 or h < 10 or w > screen_w or h > screen_h:
                continue

            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            resized = cv2.resize(template, (w, h), interpolation=interp)

            result = cv2.matchTemplate(screen_gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val
                best_h = h
                best_w = w
                best_loc_x = monitor["left"] + max_loc[0]
                best_loc_y = monitor["top"] + max_loc[1]
                
                best_pos = (
                    best_loc_x + w // 2,
                    best_loc_y + h // 2
                )

        if best_score >= THRESHOLD:
            return best_pos, best_score, best_h, best_w, best_loc_x, best_loc_y

    return None, best_score, 0, 0, 0, 0 

# 2. 鼠标移动并点击函数
def click_mouse(x, y, wait_time=0.05, y_offset=0, x_offset=0):
    final_x = int(x) + x_offset
    final_y = int(y) + y_offset 
    ctypes.windll.user32.SetCursorPos(final_x, final_y)
    time.sleep(wait_time) 
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0) 
    time.sleep(0.05) 
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0) 

# 3. 滚轮滑动函数 (正数向下，负数向上)
def scroll(times):
    for _ in range(abs(times)):
        if times > 0:
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, -120, 0) # 向下
        else:
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, 120, 0)  # 向上
        time.sleep(0.05)

# 4. 键盘操作：底层模拟打字
def type_text(text):
    for char in text:
        vk = ctypes.windll.user32.VkKeyScanW(char)
        if vk == -1:
            continue
        vk_code = vk & 0xFF
        shift_state = (vk >> 8) & 0xFF
        
        if shift_state & 1:
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
            
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        
        if shift_state & 1:
            ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
            
        time.sleep(0.01) 

# 5. 键盘操作：全选并删除
def clear_input():
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0) 
    ctypes.windll.user32.keybd_event(0x41, 0, 0, 0) 
    ctypes.windll.user32.keybd_event(0x41, 0, 2, 0) 
    ctypes.windll.user32.keybd_event(0x11, 0, 2, 0) 
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x2E, 0, 0, 0) 
    ctypes.windll.user32.keybd_event(0x2E, 0, 2, 0)
    time.sleep(0.05)

# 将整个流程封装成独立函数
def run_task():
    pos, score, _, _, _, _ = find_template("papan_pemuka.png")
    if pos:
        print(f"[1] papan_pemuka 匹配度：{score:.3f}")
        click_mouse(pos[0], pos[1])
        time.sleep(0.1)
        
        # 【修改点】找 buku 前等待 2 秒
        print(">>> 等待 2 秒 CD...")
        time.sleep(2.0)
        
        pos_buku, score_buku, _, _, _, _ = find_template("buku.png")
        if pos_buku:
            print(f"[2] buku 匹配度：{score_buku:.3f}")
            scroll(4)
            time.sleep(0.1) 
            
            pos_kat, score_kat, _, _, _, _ = find_template("kategori.png")
            if pos_kat:
                print(f"[3] kategori 匹配度：{score_kat:.3f}")
                click_mouse(pos_kat[0], pos_kat[1])
                time.sleep(0.05)
                
                pos_fik, score_fik, _, _, _, _ = find_template("fiksyen.png")
                if pos_fik:
                    print(f"[4] fiksyen 匹配度：{score_fik:.3f}")
                    click_mouse(pos_fik[0], pos_fik[1])
                    time.sleep(0.05)
                    
                    pos_bahan, score_bahan, _, _, _, _ = find_template("jenis_bahan.png")
                    if pos_bahan:
                        print(f"[5] jenis_bahan 匹配度：{score_bahan:.3f}")
                        click_mouse(pos_bahan[0], pos_bahan[1])
                        time.sleep(0.05)
                        
                        pos_fiz, score_fiz, _, _, _, _ = find_template("fizikal.png")
                        if pos_fiz:
                            print(f"[6] fizikal 匹配度：{score_fiz:.3f}")
                            click_mouse(pos_fiz[0], pos_fiz[1])
                            time.sleep(0.05)
                            
                            pos_bahasa, score_bahasa, _, _, _, _ = find_template("bahasa.png")
                            if pos_bahasa:
                                print(f"[7] bahasa 匹配度：{score_bahasa:.3f}")
                                click_mouse(pos_bahasa[0], pos_bahasa[1])
                                time.sleep(0.1) 
                                
                                pos_eng, score_eng, _, _, _, _ = find_template("english.png")
                                if pos_eng:
                                    print(f"[8] english 匹配度：{score_eng:.3f}")
                                    click_mouse(pos_eng[0], pos_eng[1])
                                    time.sleep(0.1)
                                    
                                    scroll(4)
                                    time.sleep(0.1)
                                    
                                    pos_set, score_set, _, _, _, _ = find_template("seterusnya.png")
                                    if pos_set:
                                        print(f"[9] seterusnya 匹配度：{score_set:.3f}")
                                        click_mouse(pos_set[0], pos_set[1])
                                        time.sleep(0.1)
                                        
                                        # ================= 随机打字填表阶段 =================
                                        
                                        pos_tajuk, sc_tajuk, _, _, _, _ = find_template("tajuk.png")
                                        if pos_tajuk:
                                            print(f"[10] tajuk 匹配度：{sc_tajuk:.3f}")
                                            click_mouse(pos_tajuk[0], pos_tajuk[1], y_offset=35)
                                            time.sleep(0.1)
                                            clear_input()
                                            time.sleep(0.1)
                                            
                                            title_text = generate_real_words(29)
                                            print(f"    输入标题: {title_text}")
                                            type_text(title_text)
                                            time.sleep(0.1)
                                            
                                            pos_tahun, sc_tahun, _, _, _, _ = find_template("tahun_terbitan.png")
                                            if pos_tahun:
                                                print(f"[11] tahun_terbitan 匹配度：{sc_tahun:.3f}")
                                                click_mouse(pos_tahun[0], pos_tahun[1])
                                                time.sleep(0.1)
                                                clear_input()
                                                time.sleep(0.1)
                                                
                                                print("    输入文字: 1900")
                                                type_text("1900")
                                                time.sleep(0.1)
                                                
                                                pos_penulis, sc_penulis, _, _, _, _ = find_template("penulis.png")
                                                if pos_penulis:
                                                    print(f"[12] penulis 匹配度：{sc_penulis:.3f}")
                                                    click_mouse(pos_penulis[0], pos_penulis[1])
                                                    time.sleep(0.1)
                                                    clear_input()
                                                    time.sleep(0.1)
                                                    
                                                    author_text = generate_real_words(18).strip() + "."
                                                    author_text = author_text.capitalize()
                                                    print(f"    输入作者: {author_text}")
                                                    type_text(author_text)
                                                    time.sleep(0.1)
                                                    
                                                    pos_mukasurat, sc_mukasurat, _, _, _, _ = find_template("bilangan_mukasurat.png")
                                                    if pos_mukasurat:
                                                        print(f"[13] bilangan_mukasurat 匹配度：{sc_mukasurat:.3f}")
                                                        click_mouse(pos_mukasurat[0], pos_mukasurat[1])
                                                        time.sleep(0.1)
                                                        clear_input()
                                                        time.sleep(0.1)
                                                        
                                                        first_digit = random.choice(string.digits[1:])
                                                        second_digit = random.choice(string.digits)
                                                        random_pages = first_digit + second_digit
                                                        
                                                        print(f"    输入页数: {random_pages}")
                                                        type_text(random_pages)
                                                        time.sleep(0.1)
                                                        
                                                        pos_penerbit, sc_penerbit, _, _, _, _ = find_template("penerbit.png")
                                                        if pos_penerbit:
                                                            print(f"[14] penerbit 匹配度：{sc_penerbit:.3f}")
                                                            click_mouse(pos_penerbit[0], pos_penerbit[1])
                                                            time.sleep(0.1)
                                                            clear_input()
                                                            time.sleep(0.1)
                                                            
                                                            publisher_text = generate_real_words(20).strip().title() 
                                                            while len(publisher_text) < 20:
                                                                publisher_text += " " + random.choice(ENGLISH_WORDS).capitalize()
                                                            publisher_text = publisher_text[:20]
                                                            
                                                            print(f"    输入出版社: {publisher_text}")
                                                            type_text(publisher_text)
                                                            time.sleep(0.1)
                                                            
                                                            # 【15】第二次 seterusnya 提交 (进入评价页)
                                                            pos_set2, sc_set2, _, _, _, _ = find_template("seterusnya.png")
                                                            if pos_set2:
                                                                print(f"[15] seterusnya 匹配度：{sc_set2:.3f}")
                                                                click_mouse(pos_set2[0], pos_set2[1])
                                                                time.sleep(0.5) 
                                                                
                                                                # ================= 评价与总结阶段 =================
                                                                
                                                                # 【16】penilai (智能点击最右边星星)
                                                                pos_penilai, sc_penilai, _, w_penilai, loc_x, loc_y = find_template("penilai.png")
                                                                if pos_penilai:
                                                                    print(f"[16] penilai 匹配度：{sc_penilai:.3f}")
                                                                    star_x = loc_x + w_penilai - 15
                                                                    star_y = pos_penilai[1]
                                                                    
                                                                    print(f"    正在点击最右侧星星，坐标：({star_x}, {star_y})")
                                                                    click_mouse(star_x, star_y)
                                                                    time.sleep(0.1) 
                                                                    
                                                                    # 【17】rumusan (要求超过30个单词)
                                                                    pos_rum, sc_rum, _, _, _, _ = find_template("rumusan.png")
                                                                    if pos_rum:
                                                                        print(f"[17] rumusan 匹配度：{sc_rum:.3f}")
                                                                        click_mouse(pos_rum[0], pos_rum[1], y_offset=35)
                                                                        time.sleep(0.1)
                                                                        clear_input()
                                                                        time.sleep(0.1)
                                                                        
                                                                        rumusan_text = generate_long_sentence(word_count=31)
                                                                        print(f"    输入总结: {rumusan_text}")
                                                                        type_text(rumusan_text)
                                                                        
                                                                        print(">>> 总结输入完成，等待 1.5 秒...")
                                                                        time.sleep(1.5) 
                                                                        
                                                                        print(">>> 正在向下滑动 5 次...")
                                                                        scroll(5)
                                                                        time.sleep(0.5) 
                                                                        
                                                                        # 【19】pengajaran (要求超过30个单词)
                                                                        pos_peng, sc_peng, _, _, _, _ = find_template("pengajaran.png")
                                                                        if pos_peng:
                                                                            print(f"[18] pengajaran 匹配度：{sc_peng:.3f}")
                                                                            click_mouse(pos_peng[0], pos_peng[1], y_offset=35)
                                                                            time.sleep(0.1)
                                                                            clear_input()
                                                                            time.sleep(0.1)
                                                                            
                                                                            pengajaran_text = generate_long_sentence(word_count=31)
                                                                            print(f"    输入教学价值: {pengajaran_text}")
                                                                            type_text(pengajaran_text)
                                                                            time.sleep(0.1)
                                                                            
                                                                            # 【20】最后一次 seterusnya 提交
                                                                            pos_set3, sc_set3, _, _, _, _ = find_template("seterusnya.png")
                                                                            if pos_set3:
                                                                                print(f"[19] 最终 seterusnya 匹配度：{sc_set3:.3f}")
                                                                                click_mouse(pos_set3[0], pos_set3[1])
                                                                                
                                                                                # ================= 确认和提交 =================
                                                                                print(">>> 正在等待页面响应 (0.2秒)...")
                                                                                time.sleep(0.2)
                                                                                
                                                                                print(">>> 正在向下滑动 8 次...")
                                                                                scroll(8)
                                                                                time.sleep(0.2) 
                                                                                
                                                                                # 【21】匹配 pasti.png
                                                                                pos_pasti, sc_pasti, _, _, _, _ = find_template("pasti.png")
                                                                                if pos_pasti:
                                                                                    print(f"[20] pasti 匹配度：{sc_pasti:.3f}")
                                                                                    click_mouse(pos_pasti[0], pos_pasti[1])
                                                                                    time.sleep(0.1)
                                                                                    
                                                                                    # 【22】匹配 hantar.png
                                                                                    pos_hantar, sc_hantar, _, _, _, _ = find_template("hantar.png")
                                                                                    if pos_hantar:
                                                                                        print(f"[21] hantar 匹配度：{sc_hantar:.3f}")
                                                                                        click_mouse(pos_hantar[0], pos_hantar[1])
                                                                                        
                                                                                        print(">>> 提交完成，等待 0.2 秒...")
                                                                                        time.sleep(0.2)
                                                                                        
                                                                                        print(">>> 正在向上滑动 10 次回到顶部...")
                                                                                        scroll(-10)
                                                                                        
                                                                                        print(">>> 等待 2 秒确保页面刷新...")
                                                                                        time.sleep(2.0)
                                                                                        
                                                                                        print(">>> [✔] 本轮任务结束，准备开始下一轮 Loop...")
                                                                                        return True 
                                                                                    else:
                                                                                        print(f"[X] 未找到 hantar（{sc_hantar:.3f}）")
                                                                                else:
                                                                                    print(f"[X] 未找到 pasti（{sc_pasti:.3f}）")
                                                                            else:
                                                                                print(f"[X] 未找到最后的 seterusnya（{sc_set3:.3f}）")
                                                                        else:
                                                                            print(f"[X] 未找到 pengajaran（{sc_peng:.3f}）")
                                                                    else:
                                                                        print(f"[X] 未找到 rumusan（{sc_rum:.3f}）")
                                                                else:
                                                                    print(f"[X] 未找到 penilai（{sc_penilai:.3f}）")
                                                            else:
                                                                print(f"[X] 未找到第二页的 seterusnya（{sc_set2:.3f}）")
                                                        else:
                                                            print(f"[X] 未找到 penerbit（{sc_penerbit:.3f}）")
                                                    else:
                                                        print(f"[X] 未找到 bilangan_mukasurat（{sc_mukasurat:.3f}）")
                                                else:
                                                    print(f"[X] 未找到 penulis（{sc_penulis:.3f}）")
                                            else:
                                                print(f"[X] 未找到 tahun_terbitan（{sc_tahun:.3f}）")
                                        else:
                                            print(f"[X] 未找到 tajuk（{sc_tajuk:.3f}）")
                                    else:
                                        print(f"[X] 未找到第一页的 seterusnya（{score_set:.3f}）")
                                else:
                                    print(f"[X] 未找到 english（{score_eng:.3f}）")
                            else:
                                print(f"[X] 未找到 bahasa（{score_bahasa:.3f}）")
                        else:
                            print(f"[X] 未找到 fizikal（{score_fiz:.3f}）")
                    else:
                        print(f"[X] 未找到 jenis_bahan（{score_bahan:.3f}）")
                else:
                    print(f"[X] 未找到 fiksyen（{score_fik:.3f}）")
            else:
                print(f"[X] 未找到 kategori（{score_kat:.3f}）")
        else:
            print(f"[X] 未找到 buku（{score_buku:.3f}）")
    else:
        print(f"[X] 未找到 papan_pemuka（{score:.3f}）")
    
    return False 

# ================= 多线程循环控制 =================
loop_active = False

def task_loop():
    global loop_active
    while loop_active:
        success = run_task()
        
        if loop_active: # 只有在循环没被 F7 停止时才执行等待
            if success:
                print("\n====================================")
                print(">>> 本轮任务已完成，进入 3 分 10 秒 (190秒) 冷却时间...")
                print(">>> (按 F7 可随时中止冷却并停止程序)")
                print("====================================")
                
                # 把 190 秒拆成 1 秒 1 秒地等，这样按 F7 可以立刻反应停止
                for _ in range(190):
                    if not loop_active:
                        break
                    time.sleep(1)
            else:
                print("\n[X] 某一步骤执行失败，等待 5 秒后重试...")
                time.sleep(5)

def on_press(key):
    global loop_active
    try:
        if key == keyboard.Key.f6:
            if not loop_active:
                loop_active = True
                print("\n[!] 收到 F6 指令，启动后台循环任务...")
                t = threading.Thread(target=task_loop)
                t.daemon = True
                t.start()
    except Exception as e:
        print(f"\n[!!!] 运行发生错误: {e}\n")

def on_release(key):
    global loop_active
    try:
        if key == keyboard.Key.f7:
            if loop_active:
                print("\n[!] 收到 F7 指令，正在发送停止信号... (等待当前动作结束)")
                loop_active = False
    except Exception as e:
        pass

print("====================================")
print("脚本已启动！【多线程无限循环版】")
print("按 F6 开始循环执行")
print("按 F7 随时停止循环")
print("====================================")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()