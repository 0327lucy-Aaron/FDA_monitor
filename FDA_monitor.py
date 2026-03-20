import feedparser
import smtplib
import json
import os
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

RECIPIENT_EMAIL = "0327lucy@gmail.com"
SENDER_EMAIL = os.environ.get("GMAIL_USER")
SENDER_PASSWORD = os.environ.get("GMAIL_PASS")
SENT_RECORD_FILE = "sent_drugs.json"

FDA_RSS_FEEDS = [
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/new-molecular-entity-and-new-therapeutic-biological-application-approvals/rss.xml",
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drug-approvals-and-databases/rss.xml",
]

def load_sent_records():
    if os.path.exists(SENT_RECORD_FILE):
        with open(SENT_RECORD_FILE, "r") as f:
            return json.load(f)
    return []

def save_sent_records(records):
    with open(SENT_RECORD_FILE, "w") as f:
        json.dump(records, f, indent=2)

def fetch_fda_approvals():
    new_drugs = []
    for feed_url in FDA_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                drug_info = {
                    "title": entry.get("title", "未知药品"),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", ""),
                    "id": entry.get("id", entry.get("link", "")),
                }
                new_drugs.append(drug_info)
        except Exception as e:
            print(f"抓取RSS失败: {feed_url}, 错误: {e}")
    return new_drugs

def get_label_link(drug_title):
    try:
        search_term = drug_title.split("(")[0].strip().replace(" ", "+")
        label_link = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={search_term}"
        return label_link
    except Exception as e:
        print(f"获取说明书链接失败: {e}")
    return "https://www.accessdata.fda.gov/scripts/cder/daf/"

def build_email_html(drug):
    label_link = get_label_link(drug["title"])
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #003366; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2>💊 FDA新药获批通知</h2>
            <p style="margin:0; font-size:12px;">自动监控提醒 · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        <div style="background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd;">
            <h3 style="color: #003366;">📋 药品名称</h3>
            <p style="font-size: 16px; font-weight: bold;">{drug['title']}</p>
            <h3 style="color: #003366;">📅 获批日期</h3>
            <p>{drug['published']}</p>
            <h3 style="color: #003366;">📝 摘要信息</h3>
            <p>{drug['summary'][:500]}</p>
            <div style="margin-top: 20px;">
                <a href="{drug['link']}" style="background-color: #003366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-right: 10px;">🔗 FDA官方公告</a>
                <a href="{label_link}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">📄 药品说明书</a>
            </div>
            <hr style="margin-top: 30px;">
            <p style="font-size: 11px; color: #999;">数据来源: FDA官方RSS订阅</p>
        </div>
    </body>
    </html>
    """
    return html

def send_email(drug):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🆕 FDA新药获批: {drug['title'][:60]}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    html_content = build_email_html(drug)
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print(f"✅ 邮件已发送: {drug['title']}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    print(f"🔍 开始检查FDA新药批准... {datetime.now()}")
    sent_records = load_sent_records()
    new_approvals = fetch_fda_approvals()
    new_count = 0
    for drug in new_approvals:
        drug_id = drug["id"]
        if drug_id in sent_records:
            continue
        print(f"📌 发现新药: {drug['title']}")
        if send_email(drug):
            sent_records.append(drug_id)
            new_count += 1
    save_sent_records(sent_records[-500:])
    print(f"✅ 本次检查完成，发送了 {new_count} 封新邮件")

if __name__ == "__main__":
    main()