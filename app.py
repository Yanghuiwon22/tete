import os
import time
import requests
import json
import base64

from dotenv import load_dotenv
from flask import Flask, request, redirect
from flasgger import Swagger, swag_from
from pixoo.pixoo import Channel, Pixoo

from swag import definitions
from swag import passthrough

import _helpers

import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageFilter

from bs4 import BeautifulSoup
from datetime import datetime

import qrcode


load_dotenv()

pixoo_host = os.environ.get('PIXOO_HOST', 'Pixoo64')
pixoo_screen = int(os.environ.get('PIXOO_SCREEN_SIZE', 64))
pixoo_debug = _helpers.parse_bool_value(os.environ.get('PIXOO_DEBUG', 'false'))

while not _helpers.try_to_request(f'http://{pixoo_host}/get'):
    time.sleep(30)

pixoo = Pixoo(
    pixoo_host,
    pixoo_screen,
    pixoo_debug
)

app = Flask(__name__)
app.config['SWAGGER'] = _helpers.get_swagger_config()

swagger = Swagger(app, template=_helpers.get_additional_swagger_template())
definitions.create(swagger)


def _push_immediately(_request):
    if _helpers.parse_bool_value(_request.form.get('push_immediately', default=True)):
        pixoo.push()


now = datetime.now()
def get_jinsu_menu():
    URL = 'https://coopjbnu.kr/menu/week_menu.php'
    page = requests.get(URL)
    soup = BeautifulSoup(page.text, 'html.parser')

    weekday_list = {0: "월", 1: '화', 2: '수', 3: "목", 4: "금"}

    # 진수당
    jinsu_menu = []
    menu_table = soup.find_all('tr')

    weekday = now.weekday()
    current_time = now.time()
    current_time = current_time.strftime('%H:%M:%S')
    time = datetime.strptime(current_time, '%H:%M:%S')

    if datetime.strptime('11:30:00', '%H:%M:%S') < time < datetime.strptime('14:00:00', '%H:%M:%S'):
        menu_number = 1
    # elif datetime.strptime('17:30:00', '%H:%M:%S') < time < datetime.strptime('19:00:00', '%H:%M:%S'):
    #     menu_number = 2
    else:
        menu_number = 2
    #     return '아직 시간이 아닙니다.'

    jinsu_lunch = menu_table[menu_number]  # ----> 이부분의 숫자가 바뀌면 크롤링 되는 메뉴가 바뀐다.
    jinsu_lunch_mon = jinsu_lunch.find_all('td')[weekday]  # ---> 월 0 화 1 수 2 목 3 금 4
    jinsu_lunch_mon = jinsu_lunch_mon.get_text(separator='<br/>')
    jinsu_menu.extend(jinsu_lunch_mon.split('<br/>'))
    jinsu_menu = jinsu_menu[0::2]

    # 진수당 중식 1  ------>
    # 진수당 석식 2
    # 후생관 찌개 8
    # 후생관 돌솥 9
    # 후생관 특식 10
    # 후생관 샐러드 13

    return jinsu_menu


@app.route('/', methods=['GET'])
def home():
    return redirect('/apidocs')


@app.route('/brightness/<int:percentage>', methods=['PUT'])
@swag_from('swag/set/brightness.yml')
def brightness(percentage):
    pixoo.set_brightness(percentage)

    return 'OK'


@app.route('/channel/<int:number>', methods=['PUT'])
@app.route('/face/<int:number>', methods=['PUT'])
@app.route('/visualizer/<int:number>', methods=['PUT'])
@app.route('/clock/<int:number>', methods=['PUT'])
@swag_from('swag/set/generic_number.yml')
def generic_set_number(number):
    if request.path.startswith('/channel/'):
        pixoo.set_channel(Channel(number))
    elif request.path.startswith('/face/'):
        pixoo.set_face(number)
    elif request.path.startswith('/visualizer/'):
        pixoo.set_visualizer(number)
    elif request.path.startswith('/clock/'):
        pixoo.set_clock(number)

    return 'OK'


@app.route('/screen/on/<boolean>', methods=['PUT'])
@swag_from('swag/set/generic_boolean.yml')
def generic_set_boolean(boolean):
    if request.path.startswith('/screen/on/'):
        pixoo.set_screen(_helpers.parse_bool_value(boolean))

    return 'OK'
@app.route('/text', methods=['POST'])
@swag_from('swag/draw/text2img.yml')
def text(message=None):
    image1 = np.zeros((64, 64, 3), np.uint8)
    image2 = Image.fromarray(image1)
    draw = ImageDraw.Draw(image2)

    if not message:
        raw_text = request.form.get('text')
        text = raw_text
        if len(text) > 8:
            for i in range(len(text) // 6 + 1):
                text = raw_text[i * 6:6 * (i + 1)]
                print(text)
                draw.text((4, 10 * i + 1), text, font=ImageFont.truetype("NanumGothic.ttf", 10), fill=(255, 255, 255))
        else:
            draw.text((2, 1), text, font=ImageFont.truetype("NanumGothic.ttf", 10), fill=(255, 255, 255))
    else:
        seat_number = 0
        print('========== message =========')
        print(message)
        for i in range(len(message)):
            # print(f'{i} = {text}')
            raw_text = message[i]
            print('========== raw_text ==========')
            print(raw_text)
            text = raw_text
            if len(text) > 8:
                for j in range(len(text) // 6 + 1):
                    text = raw_text[i * 6:6 * (i + 1)]
                    draw.text((2, 10 * seat_number + 1), text, font=ImageFont.truetype("NanumGothic.ttf", 10), fill=(255, 255, 255))
                    seat_number += 1
                    print(seat_number)
            else:
                draw.text((2, 1), text, font=ImageFont.truetype("NanumGothic.ttf", 10), fill=(255, 255, 255))




    for i in range(1):
        image2 = image2.filter(ImageFilter.SHARPEN)

    image2.save('text2img.png', format="PNG")
    pixoo.draw_image_at_location(
        Image.open('text2img.png'),
        int(request.form.get('x')),
        int(request.form.get('y'))
    )
    _push_immediately(request)

    return 'OK'

# @app.route('/meeting', methods=["POST"])
# @swag_from('swag/draw/meeting.yml')
# def meeting():
#     time = request.form.get('meeting')
#     text1 = f'회의중입니다'
#     text2 = f'{time}분후에 다시 들어오세요.'
#
#     image1 = np.zeros((64, 64, 3), np.uint8)
#     image2 = Image.fromarray(image1)
#     draw = ImageDraw.Draw(image2)
#
#     if len(text2) > 8:
#         for i in range(len(text2) // 8 + 1):
#             text = text2[i * 8:8 * (i + 1)]
#             draw.text((4, 8 * i + 9), text, font=ImageFont.truetype("NanumGothic.ttf", 7), fill=(255, 255, 255))
#     else:
#         draw.text((4, 1), text1, font=ImageFont.truetype("NanumGothic.ttf", 7), fill=(255, 255, 255))
#
#     image2.save('text2img.png', format="PNG")
#
#     pixoo.draw_image_at_location(
#         Image.open('text2img.png'),
#         int(request.form.get('x')),
#         int(request.form.get('y'))
#     )
#     _push_immediately(request)
#
#     return 'OK'
# @app.route('/qrcode', methods=["POST"])
# @swag_from('swag/draw/qr_text.yml')
# def qr_code_text():
#     pixoo.fill_rgb(0,0,0)
#
#     url = request.form.get('site url')
#     text = request.form.get('discription')
#     qr = qrcode.QRCode(
#         version=2,
#         error_correction=qrcode.constants.ERROR_CORRECT_M,
#         box_size=1,
#         border=3
#     )
#     qr.add_data(url)
#     qr.make(fit=True)
#     qr_img = qr.make_image(fill_color="black", back_color="white")
#     qr_img.save('./QRcode.png')
#
#
#     pixoo.draw_image_at_location(
#         Image.open('QRcode.png'),
#         14,21
#     )
#
#
#     _push_immediately(request)
#
#     return 'OK'

@app.route('/bigqrcode', methods=["POST"])
@swag_from('swag/draw/qr.yml')
def qr_code():
    # 기본적인 qr코드 생성
    url = request.form.get('site url')
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=2,
        border=1
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img.save('./QRcode.png')

    pixoo.draw_image_at_location(
        Image.open('QRcode.png'),
        # 0,0
        int(request.form.get('x')),
        int(request.form.get('y'))
    )
    _push_immediately(request)

    return 'OK'
@app.route('/menu', methods=["POST"])
@swag_from('swag/draw/menu.yml')
#version1
def menu():
    data = get_jinsu_menu()

    image1 = np.zeros((64, 64, 3), np.uint8)
    image2 = Image.fromarray(image1)
    draw = ImageDraw.Draw(image2)


    seat_number = 0

    for i in range(len(data)):
        raw_text = data[i]

        text = raw_text
        if len(text) > 6:
            for j in range(len(text) // 6 + 1):
                text = raw_text[j * 6:6 * (j + 1)]
                draw.text((2, 10 * seat_number + 1), text, font=ImageFont.truetype("NanumGothic.ttf", 10),
                          fill=(255, 255, 255))
                seat_number += 1

        else:
            draw.text((2, 10 * seat_number + 1), text, font=ImageFont.truetype("NanumGothic.ttf", 10), fill=(0, 0, 255))
            seat_number += 1

    for i in range(1):
        image2 = image2.filter(ImageFilter.SHARPEN)

    image2.save('text2img.png', format="PNG")
    pixoo.draw_image_at_location(
        Image.open('text2img.png'),
        int(request.form.get('x')),
        int(request.form.get('y'))
    )
    _push_immediately(request)

    return 'OK'

@app.route('/image', methods=['POST'])
@swag_from('swag/draw/image.yml')
def image():
    # image_path = request.form.get('image_path')
    img_file = request.files['image']
    img_file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_file.filename))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], img_file.filename)

    print(f'img_file : {img_file}')

    print('================================================')
    print(request.files)
    pixoo.draw_image_at_location(
        Image.open(file_path),
        int(request.form.get('x')),
        int(request.form.get('y'))
    )

    _push_immediately(request)

    return 'OK'

@app.route('/fill', methods=['POST'])
@swag_from('swag/draw/fill.yml')
def fill():
    pixoo.fill_rgb(
        int(request.form.get('r')),
        int(request.form.get('g')),
        int(request.form.get('b'))
    )

    _push_immediately(request)

    return 'OK'


@app.route('/line', methods=['POST'])
@swag_from('swag/draw/line.yml')
def line():
    pixoo.draw_line_from_start_to_stop_rgb(
        int(request.form.get('start_x')),
        int(request.form.get('start_y')),
        int(request.form.get('stop_x')),
        int(request.form.get('stop_y')),
        int(request.form.get('r')),
        int(request.form.get('g')),
        int(request.form.get('b'))
    )

    _push_immediately(request)

    return 'OK'


@app.route('/rectangle', methods=['POST'])
@swag_from('swag/draw/rectangle.yml')
def rectangle():
    pixoo.draw_filled_rectangle_from_top_left_to_bottom_right_rgb(
        int(request.form.get('top_left_x')),
        int(request.form.get('top_left_y')),
        int(request.form.get('bottom_right_x')),
        int(request.form.get('bottom_right_y')),
        int(request.form.get('r')),
        int(request.form.get('g')),
        int(request.form.get('b'))
    )

    _push_immediately(request)

    return 'OK'


@app.route('/pixel', methods=['POST'])
@swag_from('swag/draw/pixel.yml')
def pixel():
    pixoo.draw_pixel_at_location_rgb(
        int(request.form.get('x')),
        int(request.form.get('y')),
        int(request.form.get('r')),
        int(request.form.get('g')),
        int(request.form.get('b'))
    )

    _push_immediately(request)

    return 'OK'


@app.route('/character', methods=['POST'])
@swag_from('swag/draw/character.yml')
def character():
    pixoo.draw_character_at_location_rgb(
        request.form.get('character'),
        int(request.form.get('x')),
        int(request.form.get('y')),
        int(request.form.get('r')),
        int(request.form.get('g')),
        int(request.form.get('b'))
    )

    _push_immediately(request)

    return 'OK'


@app.route('/sendText', methods=['POST'])
@swag_from('swag/send/text.yml')
def send_text():
    pixoo.send_text(
        request.form.get('text'),
        (int(request.form.get('x')), int(request.form.get('y'))),
        (int(request.form.get('r')), int(request.form.get('g')), int(request.form.get('b'))),
        (int(request.form.get('identifier'))),
        (int(request.form.get('font'))),
        (int(request.form.get('width'))),
        (int(request.form.get('movement_speed'))),
        (int(request.form.get('direction')))
    )

    return 'OK'


def _reset_gif():
    return requests.post(f'http://{pixoo.address}/post', json.dumps({
        "Command": "Draw/ResetHttpGifId"
    })).json()


def _send_gif(num, offset, width, speed, data):
    return requests.post(f'http://{pixoo.address}/post', json.dumps({
        "Command": "Draw/SendHttpGif",
        "PicID": 1,
        "PicNum": num,
        "PicOffset": offset,
        "PicWidth": width,
        "PicSpeed": speed,
        "PicData": data
    })).json()


def _handle_gif(gif, speed, skip_first_frame):
    if gif.is_animated:
        _reset_gif()

        for i in range(1 if skip_first_frame else 0, gif.n_frames):
            gif.seek(i)

            if gif.size not in ((16, 16), (32, 32), (64, 64)):
                gif_frame = gif.resize((pixoo.size, pixoo.size)).convert("RGB")
            else:
                gif_frame = gif.convert("RGB")

            _send_gif(
                gif.n_frames + (-1 if skip_first_frame else 0),
                i + (-1 if skip_first_frame else 0),
                gif_frame.width,
                speed,
                base64.b64encode(gif_frame.tobytes()).decode("utf-8")
            )
    else:
        pixoo.draw_image(gif)
        pixoo.push()


@app.route('/sendGif', methods=['POST'])
@swag_from('swag/send/gif.yml')
def send_gif():
    _handle_gif(
        Image.open(request.files['gif'].stream),
        int(request.form.get('speed')),
        _helpers.parse_bool_value(request.form.get('skip_first_frame', default=False))
    )

    return 'OK'


@app.route('/download/gif', methods=['POST'])
@swag_from('swag/download/gif.yml')
def download_gif():
    try:
        response = requests.get(
            request.form.get('url'),
            stream=True,
            timeout=int(request.form.get('timeout')),
            verify=_helpers.parse_bool_value(request.form.get('ssl_verify', default=True))
        )

        response.raise_for_status()

        _handle_gif(
            Image.open(response.raw),
            int(request.form.get('speed')),
            _helpers.parse_bool_value(request.form.get('skip_first_frame', default=False))
        )
    except (requests.exceptions.RequestException, OSError, IOError) as e:
        return f'Error downloading the GIF: {e}', 400

    return 'OK'


@app.route('/download/image', methods=['POST'])
@swag_from('swag/download/image.yml')
def download_image():
    try:
        response = requests.get(
            request.form.get('url'),
            stream=True,
            timeout=int(request.form.get('timeout')),
            verify=_helpers.parse_bool_value(request.form.get('ssl_verify', default=True))
        )

        response.raise_for_status()

        pixoo.draw_image_at_location(
            Image.open(response.raw),
            int(request.form.get('x')),
            int(request.form.get('y'))
        )

        _push_immediately(request)
    except (requests.exceptions.RequestException, OSError, IOError) as e:
        return f'Error downloading the image: {e}', 400

    return 'OK'


passthrough_routes = {
    # channel ...
    '/passthrough/channel/setIndex': passthrough.create(*passthrough.channel_set_index),
    '/passthrough/channel/setCustomPageIndex': passthrough.create(*passthrough.channel_set_custom_page_index),
    '/passthrough/channel/setEqPosition': passthrough.create(*passthrough.channel_set_eq_position),
    '/passthrough/channel/cloudIndex': passthrough.create(*passthrough.channel_cloud_index),
    '/passthrough/channel/getIndex': passthrough.create(*passthrough.channel_get_index),
    '/passthrough/channel/setBrightness': passthrough.create(*passthrough.channel_set_brightness),
    '/passthrough/channel/getAllConf': passthrough.create(*passthrough.channel_get_all_conf),
    '/passthrough/channel/onOffScreen': passthrough.create(*passthrough.channel_on_off_screen),
    # sys ...
    '/passthrough/sys/logAndLat': passthrough.create(*passthrough.sys_log_and_lat),
    '/passthrough/sys/timeZone': passthrough.create(*passthrough.sys_timezone),
    # device ...
    '/passthrough/device/setUTC': passthrough.create(*passthrough.device_set_utc),
    '/passthrough/device/SetScreenRotationAngle': passthrough.create(*passthrough.device_set_screen_rotation_angle),
    '/passthrough/device/SetMirrorMode': passthrough.create(*passthrough.device_set_mirror_mode),
    '/passthrough/device/getDeviceTime': passthrough.create(*passthrough.device_get_device_time),
    '/passthrough/device/setDisTempMode': passthrough.create(*passthrough.device_set_dis_temp_mode),
    '/passthrough/device/setTime24Flag': passthrough.create(*passthrough.device_set_time_24_flag),
    '/passthrough/device/setHighLightMode': passthrough.create(*passthrough.device_set_high_light_mode),
    '/passthrough/device/setWhiteBalance': passthrough.create(*passthrough.device_set_white_balance),
    '/passthrough/device/getWeatherInfo': passthrough.create(*passthrough.device_get_weather_info),
    '/passthrough/device/playBuzzer': passthrough.create(*passthrough.device_play_buzzer),
    # tools ...
    '/passthrough/tools/setTimer': passthrough.create(*passthrough.tools_set_timer),
    '/passthrough/tools/setStopWatch': passthrough.create(*passthrough.tools_set_stop_watch),
    '/passthrough/tools/setScoreBoard': passthrough.create(*passthrough.tools_set_score_board),
    '/passthrough/tools/setNoiseStatus': passthrough.create(*passthrough.tools_set_noise_status),
    # draw ...
    '/passthrough/draw/sendHttpText': passthrough.create(*passthrough.draw_send_http_text),
    '/passthrough/draw/clearHttpText': passthrough.create(*passthrough.draw_clear_http_text),
    '/passthrough/draw/sendHttpGif': passthrough.create(*passthrough.draw_send_http_gif),
    '/passthrough/draw/resetHttpGifId': passthrough.create(*passthrough.draw_reset_http_gif_id),
}


def _passthrough_request(passthrough_request):
    return requests.post(f'http://{pixoo.address}/post', json.dumps(passthrough_request.json)).json()


for _route, _swag in passthrough_routes.items():
    exec(f"""
@app.route('{_route}', methods=['POST'], endpoint='{_route}')
@swag_from({_swag}, endpoint='{_route}')
def passthrough_{list(passthrough_routes.keys()).index(_route)}():
    return _passthrough_request(request)
        """)


@app.route('/divoom/device/lan', methods=['POST'])
@swag_from('swag/divoom/device/return_same_lan_device.yml')
def divoom_return_same_lan_device():
    return _helpers.divoom_api_call('Device/ReturnSameLANDevice').json()


@app.route('/divoom/channel/dial/types', methods=['POST'])
@swag_from('swag/divoom/channel/get_dial_type.yml')
def divoom_get_dial_type():
    return _helpers.divoom_api_call('Channel/GetDialType').json()


@app.route('/divoom/channel/dial/list', methods=['POST'])
@swag_from('swag/divoom/channel/get_dial_list.yml')
def divoom_get_dial_list():
    return _helpers.divoom_api_call(
        'Channel/GetDialList',
        {
            'DialType': request.form.get('dial_type', default='Game'),
            'Page': int(request.form.get('page_number', default='1'))
        }
    ).json()


if __name__ == '__main__':
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.run(
        debug=_helpers.parse_bool_value(os.environ.get('PIXOO_REST_DEBUG', 'false')),
        # host=os.environ.get('PIXOO_REST_HOST', '127.0.0.1'),
        # port=os.environ.get('PIXOO_REST_PORT', '5000')
        host=os.environ.get('PIXOO_REST_HOST', '0.0.0.0'),
        port=os.environ.get('PIXOO_REST_PORT', '5000')
    )
