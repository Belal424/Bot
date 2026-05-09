import requests
import time
import threading
import json
import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# إعدادات البوت
BOT_TOKEN = '8663038181:AAH3SSr9bVrFI1LePkc77M6KCjONGO_Zprw'
bot = telebot.TeleBot(BOT_TOKEN)

USERS_FILE = 'bot_users.json'
URL_LINK_1 = 'https://www.tazkarti.com/data/TicketPrice-AvailableSeats-2504.json'
URL_LINK_2 = 'https://www.tazkarti.com/data/matches-list-json.json'

AHLY_KEYWORDS = ['اهلي', 'اهلى', 'أهلي', 'أهلى', 'ahly', 'ahli']
ZAMALEK_KEYWORDS = ['زمالك', 'الزمالك', 'zamalek']

# --- إعدادات صفحة الويب الوهمية عشان Render ---
app = Flask(__name__)

@app.route('/')
def alive():
    return "البوت يعمل بنجاح 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- دوال التعامل مع المستخدمين ---
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return {str(chat_id): 'both' for chat_id in data}
                return data
            except:
                return {}
    return {}

def save_user_pref(chat_id, pref):
    users = load_users()
    users[str(chat_id)] = pref
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def send_to_filtered_users(message, match_is_ahly, match_is_zamalek):
    users = load_users()
    for chat_id, pref in users.items():
        if (pref == 'ahly' and match_is_ahly) or \
           (pref == 'zamalek' and match_is_zamalek) or \
           (pref == 'both'):
            try:
                bot.send_message(chat_id, message)
            except Exception as e:
                pass

# --- أوامر البوت والأزرار ---
@bot.message_handler(commands=['start'])
def start_command(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🦅 الأهلي", callback_data="pref_ahly"),
        InlineKeyboardButton("🏹 الزمالك", callback_data="pref_zamalek"),
        InlineKeyboardButton("⚽ الاتنين", callback_data="pref_both")
    )
    bot.reply_to(message, "أهلاً بيك يا غالي! اختار عايز يوصلك إشعارات تذاكر لأي فريق؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pref_'))
def callback_query(call):
    chat_id = call.message.chat.id
    pref = call.data.split('_')[1]
    
    save_user_pref(chat_id, pref)
    
    if pref == "ahly":
        team_name = "النادي الأهلي 🦅"
    elif pref == "zamalek":
        team_name = "نادي الزمالك 🏹"
    else:
        team_name = "الأهلي والزمالك ⚽"
        
    bot.answer_callback_query(call.id, "تم حفظ اختيارك!")
    new_text = f"تم التفعيل بنجاح! هبعتلك إشعار فور نزول تذاكر {team_name}."
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=new_text)

# --- دوال الفحص ---
def check_team_in_keywords(team_ar, team_en):
    name_ar = (team_ar or "").lower()
    name_en = (team_en or "").lower()
    is_ahly = any(kw in name_ar or kw in name_en for kw in AHLY_KEYWORDS)
    is_zamalek = any(kw in name_ar or kw in name_en for kw in ZAMALEK_KEYWORDS)
    return is_ahly, is_zamalek

def tazkarti_checker():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.tazkarti.com/'
    }
    
    notified_matches_link2 = []
    
    while True:
        try:
            res2 = requests.get(URL_LINK_2, headers=headers, timeout=10)
            if res2.status_code == 200:
                data2 = res2.json()
                matches = data2.get('data', data2) if isinstance(data2, dict) else data2
                
                if isinstance(matches, list):
                    for match in matches:
                        t1_ar, t1_en = match.get('teamNameAr1', ''), match.get('teamName1', '')
                        t2_ar, t2_en = match.get('teamNameAr2', ''), match.get('teamName2', '')
                        
                        is_ahly_t1, is_zamalek_t1 = check_team_in_keywords(t1_ar, t1_en)
                        is_ahly_t2, is_zamalek_t2 = check_team_in_keywords(t2_ar, t2_en)
                        
                        match_is_ahly = is_ahly_t1 or is_ahly_t2
                        match_is_zamalek = is_zamalek_t1 or is_zamalek_t2
                        
                        if match_is_ahly or match_is_zamalek:
                            match_id = match.get('matchId')
                            
                            if match_id and match_id not in notified_matches_link2:
                                team1 = match.get('teamNameAr1') or match.get('teamName1') or 'فريق 1'
                                team2 = match.get('teamNameAr2') or match.get('teamName2') or 'فريق 2'
                                kickoff = match.get('kickOffTime', 'غير محدد').replace('T', ' ')
                                stadium = match.get('stadiumNameAr') or match.get('stadiumName') or 'غير محدد'
                                tournament = match.get('tournament', {}).get('nameAr', 'بطولة غير محددة')
                                
                                msg2 = (f"🔥 تذاكر متاحة الآن!\n\n"
                                        f"🏆 البطولة: {tournament}\n"
                                        f"⚽ المباراة: {team1} ضد {team2}\n"
                                        f"📅 موعد الانطلاق: {kickoff}\n"
                                        f"🏟️ الملعب: {stadium}\n\n"
                                        f"رابط الحجز: https://www.tazkarti.com")
                                
                                send_to_filtered_users(msg2, match_is_ahly, match_is_zamalek)
                                notified_matches_link2.append(match_id)
        except Exception as e:
            pass
        time.sleep(20)

if __name__ == '__main__':
    # 1. تشغيل السيرفر الوهمي عشان Render
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    # 2. تشغيل فحص التذاكر
    checker_thread = threading.Thread(target=tazkarti_checker)
    checker_thread.daemon = True
    checker_thread.start()
    
    # 3. تشغيل البوت
    print("تم التشغيل بنجاح...")
    bot.polling(none_stop=True)