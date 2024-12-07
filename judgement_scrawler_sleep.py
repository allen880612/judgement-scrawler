import os
import sys
import datetime
import re
import time
import random
from multiprocessing import Process, Semaphore
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotVisibleException,
    ElementNotSelectableException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait

class JudgementScrawler:
    def __init__(self):
        # 定義 5 組不同的 User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)',
            'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)'
        ]
        # 隨機選擇一個 User-Agent
        selected_agent = random.choice(user_agents)
        # 初始化 Driver
        self.driver = Driver(
            disable_gpu=False,
            agent=selected_agent,
            incognito=True,
            headless=True,
            browser='chrome',
            uc=True,
            no_sandbox=True,
        )
        self.wait = WebDriverWait(
            self.driver, 10, poll_frequency=1,
            ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException]
        )
        self.driver.get('https://judgment.judicial.gov.tw/FJUD/default.aspx')

    def get_judgement_links_count(self, search_str, court_name):
        time.sleep(random.uniform(3, 5))  # 加入隨機延遲
        # 搜尋輸入和提交
        self.wait.until(EC.visibility_of_element_located((By.XPATH, '//input[@id="btnSimpleQry"]')))
        submit_button = self.driver.find_element(By.XPATH, '//input[@id="btnSimpleQry"]')
        search_input = self.driver.find_element(By.XPATH, '//input[@id="txtKW"]')
        search_input.send_keys(search_str)
        submit_button.click()

        # 切換到結果框架
        self.wait.until(EC.visibility_of_element_located((By.ID, "iframe-data")))
        frame = self.driver.find_element(By.ID, "iframe-data")
        self.driver.switch_to.frame(frame)

        # 獲取總頁數
        try:
            self.wait.until(EC.visibility_of_element_located((By.ID, "plPager")))
            pages = self.driver.find_element(By.ID, "plPager").text.split(" . ")[0].strip().split(" ")[1]
            return pages
        except TimeoutException:
            print("未找到結果頁面。")
            return 0

    def get_judgement_links(self, search_str, court_name, judgement_type):
        # 初始化
        self.driver.get('https://judgment.judicial.gov.tw/FJUD/Default_AD.aspx')
        judgement_links = []
        today = datetime.date.today()
        year_now = today.year - 1911

        # 定義內部函數
        def get_month_days(year, month):
            normal_month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            special_month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            year += 1911
            if (year % 400 == 0 or (year % 100 != 0 and year % 4 == 0)):
                return special_month_days[month - 1]
            else:
                return normal_month_days[month - 1]

        def get_year_months(year):
            today = datetime.date.today()
            year_now = today.year - 1911
            month_now = today.month
            if (year == year_now):
                return month_now
            else:
                return 12

        def reset_input():
            self.driver.delete_all_cookies()
            self.driver.get('https://judgment.judicial.gov.tw/FJUD/Default_AD.aspx')
            self.wait.until(EC.visibility_of_element_located((By.XPATH, '//button[@id="btnReset"]')))
            reset_button = self.driver.find_element(By.XPATH, '//button[@id="btnReset"]')
            reset_button.click()

        # 搜尋過去 N 年 (目前使用案例，往回追 7 年就足夠)
        month_break_count = 0
        for searching_year in range(year_now, year_now - 8, -1):
            searching_months = get_year_months(searching_year)
            if (month_break_count > 12):
                month_break_count = 0
                break
            for searching_month in range(searching_months, 0, -1):
                month_days = get_month_days(searching_year, searching_month)
                month_days_parts = [
                    month_days // 5,
                    month_days // 5 * 2,
                    month_days // 5 * 3,
                    month_days // 5 * 4,
                    month_days,
                ]

                month_result_count = 0
                print(f"[{court_name}] 開始抓取 {searching_year} 年度 {searching_month} 月的案件")
                for part in range(5):
                    searching_month_days = month_days_parts[part]
                    try:
                        self.wait.until(EC.visibility_of_element_located(
                            (By.XPATH, '//table[@class="search-table"]/tbody/tr/td/label[@id="vtype_C"]')))
                    except TimeoutException:
                        print("未找到搜尋表單，嘗試重置輸入。")
                        reset_input()
                        continue
                    # 填寫搜尋條件
                    self.wait.until(EC.visibility_of_element_located((By.XPATH, '//input[@id="btnQry"]')))
                    self.wait.until(EC.visibility_of_element_located((By.XPATH, '//input[@id="jud_kw"]')))
                    submit_button = self.driver.find_element(By.XPATH, '//input[@id="btnQry"]')
                    search_input = self.driver.find_element(By.XPATH, '//input[@id="jud_kw"]')

                    # 輸入日期
                    from_year_input = self.driver.find_element(By.XPATH, '//input[@id="dy1"]')
                    from_month_input = self.driver.find_element(By.XPATH, '//input[@id="dm1"]')
                    from_day_input = self.driver.find_element(By.XPATH, '//input[@id="dd1"]')
                    to_year_input = self.driver.find_element(By.XPATH, '//input[@id="dy2"]')
                    to_month_input = self.driver.find_element(By.XPATH, '//input[@id="dm2"]')
                    to_day_input = self.driver.find_element(By.XPATH, '//input[@id="dd2"]')

                    # 清空輸入框
                    from_year_input.clear()
                    from_month_input.clear()
                    from_day_input.clear()
                    to_year_input.clear()
                    to_month_input.clear()
                    to_day_input.clear()
                    search_input.clear()

                    from_year_input.send_keys(searching_year)
                    to_year_input.send_keys(searching_year)

                    from_month_input.send_keys(searching_month)
                    to_month_input.send_keys(searching_month)

                    if (part == 0):
                        from_day_input.send_keys(1)
                    else:
                        from_day_input.send_keys(month_days_parts[part - 1])

                    to_day_input.send_keys(searching_month_days)

                    search_input.send_keys(search_str)
                    submit_button.click()

                    time.sleep(random.uniform(3, 5))  # 加入隨機延遲

                    # 檢查結果數量
                    try:
                        result_count_element = self.driver.find_element(By.XPATH, "//div[@id='result-count']/ul/li/a/span")
                        result_count = int(result_count_element.text)
                        month_result_count += result_count
                    except NoSuchElementException:
                        print("未找到結果數量，可能沒有結果。")
                        reset_input()
                        continue

                    # 獲取連結
                    list_href_elements = self.driver.find_elements(By.XPATH, "//div[@id='collapseGrpCourt']/div[@class='panel-body']/ul/li")

                    # 所有法院
                    if (court_name == ''):
                        list_href = self.driver.find_element(By.XPATH, "//*[@id='result-count']/ul/li/a").get_attribute("href")
                    else:
                        list_href = None
                        for l in list_href_elements:
                            type_text = l.text
                            if (court_name in type_text):
                                list_href = l.find_element(By.TAG_NAME, "a").get_attribute("href")
                                break

                    if (not list_href):
                        reset_input()
                        break

                    self.driver.get(list_href)
                    time.sleep(random.uniform(3, 5))  # 加入隨機延遲

                    # 獲取頁數
                    try:
                        pages_text = self.driver.find_element(By.XPATH, "//div[@id='plPager']/span").text
                        pages = int(pages_text.split(" / ")[1].split(" ")[0])
                    except (NoSuchElementException, IndexError):
                        pages = 1

                    # 獲取每頁的連結
                    for _ in range(pages):
                        judgement_list = self.driver.find_elements(By.XPATH, "//table[@id='jud']/tbody/tr/td/a")
                        for j in judgement_list:
                            judgement_links.append(j.get_attribute("href"))

                        # 點擊下一頁
                        try:
                            next_page_button = self.driver.find_element(By.XPATH, "//div[@id='plPager']/span/a[@id='hlNext']")
                            next_page_button.click()
                            time.sleep(3)  # 加入隨機延遲
                        except NoSuchElementException:
                            break
                    reset_input()
                    print(f"已抓取案件總數: {len(judgement_links)}")
                    time.sleep(random.uniform(3, 5))  # 加入隨機延遲

                if (month_result_count == 0):
                    print(f"沒有搜尋到 {searching_year} 年度 {searching_month} 月的案件。")
                    month_break_count += 1
                    reset_input()
                    continue
                else:
                    month_break_count = 0
        print(f"[{court_name}] 案件連結抓取完畢，總共 {len(judgement_links)} 件，開始下載案件內容。")
        return judgement_links

    def get_all_judgement_page(self, search_str, court_name, judgement_type):
        links = self.get_judgement_links_count(search_str, court_name)
        if (judgement_type == ''):
            print(f"總共 {links} 件")
        os.makedirs('judgement_docs', exist_ok=True)
        judgement_links = self.get_judgement_links(search_str, court_name, judgement_type)

        def get_judgement_page(link):
            link_id = link.split('&id=')[1].split('&ot=')[0]
            pure_page_link = 'https://judgment.judicial.gov.tw/EXPORTFILE/reformat.aspx?type=JD' + '&id=' + link_id
            self.driver.get(pure_page_link)
            time.sleep(random.uniform(3, 5))  # 加入隨機延遲

            html = self.driver.page_source
            text = re.sub(r'<[^>]+>', '\n', html)
            try:
                text = text.split('裁判字號：')[1].split('資料解析中...請稍後')[0].replace('&nbsp;', ' ').strip('\n')
            except IndexError:
                print(f"無法解析內容：{pure_page_link}")
                return
            title = text.split('\n')[0]
            if (title == '\\t系統訊息' or title == '系統訊息'):
                return
            filename = os.path.join('judgement_docs', f'{title}.txt')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
                print(f"{title}.txt 儲存完成")

        count = 0
        for link in judgement_links:
            get_judgement_page(link)
            count += 1
            print(f"已儲存案件數: {count}/{len(judgement_links)}")
            time.sleep(3)
        print("案件全數抓取完成，程式結束。")

def get_single_judgement_docs(court_name):
    scrawler = JudgementScrawler()
    scrawler.get_all_judgement_page(search_str='加密貨幣', court_name=court_name, judgement_type='')
    scrawler.driver.quit()

def get_all_judgement_docs():
    court_name_list = [
        "臺灣臺北地方法院", "臺灣士林地方法院", "臺灣新北地方法院", "臺灣宜蘭地方法院",
        "臺灣基隆地方法院", "臺灣桃園地方法院", "臺灣新竹地方法院", "臺灣苗栗地方法院",
        "臺灣臺中地方法院", "臺灣彰化地方法院", "臺灣南投地方法院", "臺灣雲林地方法院",
        "臺灣嘉義地方法院", "臺灣臺南地方法院", "臺灣高雄地方法院", "臺灣橋頭地方法院",
        "臺灣花蓮地方法院", "臺灣臺東地方法院", "臺灣澎湖地方法院", "福建高等法院金門分院",
        "福建金門地方法院", "福建連江地方法院"
    ]
    # court_name_list = ["臺灣臺北地方法院", "臺灣士林地方法院", "臺灣新北地方法院"]

    # Thread > Process，driver 仍會搶奪，即時加上 wait unitil 仍常常會找不到頁面元件
    # 故先採用單線程處理，依照法院名稱逐一處理
    for court_name in court_name_list:
        print(f"開始處理法院：{court_name}")
        get_single_judgement_docs(court_name)
        time.sleep(2)  # 加入延遲，避免對伺服器造成壓力

#     processes = []
#     max_processes = 3  # 控制同時運行的進程數量
#     semaphore = Semaphore(max_processes)

#     for court_name in court_name_list:
#         semaphore.acquire()
#         print(f"開始處理法院：{court_name}")
#         p = Process(target=process_wrapper, args=(court_name, semaphore))
#         processes.append(p)
#         p.start()
#         time.sleep(random.uniform(1, 2))  # 控制啟動進程的頻率

#     for p in processes:
#         p.join()

# def process_wrapper(court_name, semaphore):
#     try:
#         get_single_judgement_docs(court_name)
#     finally:
#         semaphore.release()

if __name__ == "__main__":
    get_all_judgement_docs()
