from bs4 import BeautifulSoup
import pandas as pd
import urllib.request,sys,time
import requests
from datetime import datetime

now = datetime.now()
def get_jinsu_menu():
    URL = 'https://coopjbnu.kr/menu/week_menu.php'
    page = requests.get(URL)
    soup = BeautifulSoup(page.text, 'html.parser')

    weekday_list = {0:"월", 1:'화', 2:'수', 3:"목", 4:"금"}

    # 진수당
    jinsu_menu = []
    menu_table = soup.find_all('tr')

    weekday = now.weekday()
    current_time = now.time()
    current_time = current_time.strftime('%H:%M:%S')
    time = datetime.strptime(current_time, '%H:%M:%S')

    if datetime.strptime('11:30:00', '%H:%M:%S') < time < datetime.strptime('14:00:00', '%H:%M:%S'):
        jinsu_lunch = menu_table[1]  # ----> 이부분의 숫자가 바뀌면 크롤링 되는 메뉴가 바뀐다.
        jinsu_lunch_mon = jinsu_lunch.find_all('td')[weekday]  # ---> 월 0 화 1 수 2 목 3 금 4
        jinsu_lunch_mon = jinsu_lunch_mon.get_text(separator='<br/>')
        jinsu_menu.extend(jinsu_lunch_mon.split('<br/>'))
        jinsu_menu = jinsu_menu[0::2]

        return jinsu_menu
    else:
        pass


    # 진수당 중식 1  ------>
    # 진수당 석식 2
    # 후생관 찌개 8
    # 후생관 돌솥 9
    # 후생관 특식 10
    # 후생관 샐러드 13

    return jinsu_menu

get_jinsu_menu()
