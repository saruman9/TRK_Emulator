__author__ = 'neo'
# -*- coding: utf-8 -*-

import kivy
kivy.require('1.8.0')

from kivy.uix.popup import Popup
import re
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.app import Builder
from kivy.clock import Clock


############################################
# Класс типа топлива и взаимодейтсвие с ним
############################################


class Fuel(object):

    sCaption = ''
    sType = ''
    fVolume = 0.0
    fMaxVolume = 0.0
    fPrice = 0.0
    bBusy = False
    bGun = False
    fCapacity = 0.0
    iPercent = 0
    iStatus = 5

    def __init__(self, sCaption='Колонка 1', sType='98', fVolume=0, fMaxVolume=0, fPrice=666.0, bBusy=False, bGun=False, fCapacity=0,
                 iPercent=0, iStatus=5, **kwargs):
        self.sCaption = sCaption
        self.sType = sType
        self.fVolume = fVolume
        self.fMaxVolume = fMaxVolume
        self.fPrice = fPrice
        self.bBusy = bBusy
        self.fCapacity = fCapacity
        self.iPercent = iPercent
        self.bGun = bGun
        self.iStatus = iStatus
        super(Fuel, self).__init__(**kwargs)

    def Fueling(self, dt):
        self.bGun = True
        if self.iPercent >= 100:
            self.fCapacity = 0
            self.iPercent = 0
            self.iStatus = 5
            self.bBusy = False
            return False
        self.iPercent += 1



#################
# Класс запроса
#################


class Request(object):

    SOH = 0x01
    TRK_No = '99'
    Command = '0'
    STX = 0x02
    Price = '000000000'
    Volume = '000000'
    Error = '00'
    Code = '00'
    ETX = 0x03
    CRC = 0x00

    def __init__(self, TRK_No='99', Price='000000000', Volume='000000', Error='00', Code='05', **kwargs):
        self.TRK_No = TRK_No
        self.Price = Price
        self.Volume = Volume
        self.Error = Error
        self.Code = Code
        super(Request, self).__init__(**kwargs)

    def StateToStr(self):
        self.CRC_string()
        string = chr(self.SOH) + '{:02d}'.format(int(self.TRK_No)) + self.Command + \
                 chr(self.STX) + '{:09d}'.format(int(self.Price)) + \
                 '{:06d}'.format(int(self.Volume)) + self.Error + \
                 self.Code + chr(self.ETX) + self.CRC
        return string

    def CRC_string(self):
        string = '{:02d}'.format(int(self.TRK_No)) + self.Command +\
                 chr(self.STX) + '{:09d}'.format(int(self.Price)) +\
                 '{:06d}'.format(int(self.Volume)) + self.Error +\
                 self.Code + chr(self.ETX)
        self.CRC = chr(self.xor_string(string))

    @staticmethod
    def xor_string(string):
        xor = 0x0
        for char in string:
            xor ^= ord(char)
        return xor

    def Check(self, string):
        if ord(string[0]) != 0x01:
            print("Error SOH")
            return 1
        elif int(string[1:3]) > 99:
            print("Error TRK_No")
            return 1
        elif 0x39 < ord(string[3]) < 0x30:
            print("Error Command")
            return 1
        elif ord(string[4]) != 0x02:
            print("Error STX")
            return 1
        elif int(string[5:14]) > 999999999:
            print("Error Price")
            return 1
        elif int(string[14:20]) > 999999:
            print("Error Volume")
            return 1
        elif int(string[20:22]) > 3:
            print("Error Error")
            return 1
        elif int(string[22:24]) > 7:
            print("Error Code")
            return 1
        elif ord(string[24]) != 0x03:
            print("Error ETX")
            return 1
        elif self.xor_string(string[1:25]) != ord(string[25]):
            print("Error CRC, inp = 0x{:x}, chk = 0x{:x}".format(ord(string[25]), self.xor_string(string[1:24])))
            return 1
        else:
            return 0


################
# Класс ответа
################


class State(Fuel, Request, object):

    rSOH = 0x01
    rTRK_No = '99'
    rCommand = '0'
    rSTX = 0x02
    rPrice = '000000000'
    rVolume = '000000'
    rError = '00'
    rCode = '00'
    rETX = 0x03
    rCRC = 0x00


    def __init__(self, **kwargs):
        super(State, self).__init__(**kwargs)
        #Request.__init__(self)
        #Fuel.__init__(self)

    def StrToState(self, string):
        self.rTRK_No = string[1:3]
        self.rCommand = string[3]
        self.rPrice = string[5:14]
        self.rVolume = string[14:20]
        self.rError = string[20:22]
        self.rCode = string[22:24]
        self.rCRC = string[25]

    def Answer(self, string):
        self.StrToState(string)
        if int(self.rTRK_No) < 0 or int(self.rTRK_No) > 8:
            self.Command = self.rCommand
            self.TRK_No = self.rTRK_No
            self.Code = '07'
            self.Error_1()
            return self.StateToStr()
        if self.rCommand == '4':
            self.Answer_4()
            return self.StateToStr()
        elif self.rCommand == '1':
            self.Answer_1()
            return self.StateToStr()
        elif self.rCommand == '7':
            self.Answer_7()
            return self.StateToStr()
        elif self.rCommand == '5':
            self.Answer_5()
            return self.StateToStr()
        elif self.rCommand == '6':
            self.Answer_6()
            return self.StateToStr()
        elif self.rCommand == '3':
            self.Answer_3()
            return  self.StateToStr()

    def Answer_4(self):
        self.Command = self.rCommand
        self.Volume = int(self.fCapacity - (self.fCapacity * (self.iPercent / 100.))) * 1000
        self.Price = int(int(self.Volume) / 1000. * self.fPrice * 100)
        self.Code = '{:02d}'.format(self.iStatus)

    def Answer_1(self):
        self.Command = self.rCommand
        if int(self.rVolume) != 0:
            self.fCapacity = int(self.rVolume) / 1000.
            self.Volume = self.rVolume
            self.Price = str(int(int(self.rVolume) / 1000. * self.fPrice * 100))
            self.Code = '01'
            self.iStatus = 1
        elif int(self.rPrice) != 0:
            self.fCapacity = int(self.rPrice) / 100. / self.fPrice
            self.Volume = str(int(int(self.rPrice) / 100. / self.fPrice * 1000))
            self.Price = str(int(int(self.Volume) / 1000. * self.fPrice * 100))
            self.Code = '01'
            self.iStatus = 1
        elif int(self.rVolume) == 0:
            pass

    def Answer_5(self):
        self.Command = self.rCommand
        self.fVolume -= self.fCapacity
        Clock.schedule_interval(self.Fueling, 1 / (0.83 / (self.fCapacity / 100)))
        self.bBusy = True
        self.iStatus = 3
        self.Code = '03'

    def Answer_6(self):
        self.Command = self.rCommand
        self.Code = '04'
        self.iStatus = 4
        Clock.unschedule(self.Fueling)
        self.Volume = int((self.fCapacity - (self.fCapacity * (self.iPercent / 100.))) * 1000)

    def Answer_7(self):
        self.Command = self.rCommand
        self.Code = '05'
        self.iStatus = 5
        self.bBusy = False
        self.Volume = int((self.fCapacity - (self.fCapacity * (self.iPercent / 100.))) * 1000)
        self.fVolume += self.fCapacity * (1 - (self.iPercent / 100.))
        self.fCapacity = 0.
        self.iPercent = 0

    def Answer_3(self):
        self.Command = self.rCommand
        self.Price = '000000000'
        self.Volume = '000000'
        self.Error = self.rError
        self.Code = self.rCode
        self.iStatus = int(self.rCode)

    def Answer_9(self):
        pass

    def Error_1(self):
        self.Error = '01'

#################################################
# Типы топлива и типы протоколов
#################################################

f98_1 = State(sCaption='Колонка 1', sType='98', fVolume=1000, fMaxVolume=1000, fPrice=36.60, TRK_No='1')
f95_1 = State(sCaption='Колонка 1', sType='95', fVolume=1000, fMaxVolume=1000, fPrice=33.00, TRK_No='2')
f92_1 = State(sCaption='Колонка 1', sType='92', fVolume=1000, fMaxVolume=1000, fPrice=30.10, TRK_No='3')
fDT_1 = State(sCaption='Колонка 1', sType='ДТ', fVolume=1000, fMaxVolume=1000, fPrice=32.45, TRK_No='4')
f98_2 = State(sCaption='Колонка 2', sType='98', fVolume=1000, fMaxVolume=1000, fPrice=36.60, TRK_No='5')
f95_2 = State(sCaption='Колонка 2', sType='95', fVolume=1000, fMaxVolume=1000, fPrice=33.00, TRK_No='6')
f92_2 = State(sCaption='Колонка 2', sType='92', fVolume=1000, fMaxVolume=1000, fPrice=30.10, TRK_No='7')
fDT_2 = State(sCaption='Колонка 2', sType='ДТ', fVolume=1000, fMaxVolume=1000, fPrice=32.45, TRK_No='8')

#f95_1 = Fuel('Колонка 1', '95', 1000, 1000, 33.00)
#f92_1 = Fuel('Колонка 1', '92', 1000, 1000, 30.10)
#fDT_1 = Fuel('Колонка 1', 'ДТ', 1000, 1000, 32.45)
#f98_2 = Fuel('Колонка 2', '98', 1000, 1000, 36.60)
#f95_2 = Fuel('Колонка 2', '95', 1000, 1000, 33.00)
#f92_2 = Fuel('Колонка 2', '92', 1000, 1000, 30.10)
#fDT_2 = Fuel('Колонка 2', 'ДТ', 1000, 1000, 32.45)

#################
# Шаблон топлива
# Шаблон запроса
#################

fMain = State()
qRequest = Request()
qAnswer = State()

############################################################
# Canvas в kv коде (при __init__ не инициализируется размер)
############################################################

kv_string = """
<MainScreen>:
    FloatLayout:

        canvas:
            Rectangle:
                pos: self.center_x, 0
                size: 3, self.height"""
Builder.load_string(kv_string)

##################################################
# Переобъявление классов: Label, Button, TextInput
##################################################


class DynamicFontLabel(Label):

    def __init__(self, **kwargs):
        super(DynamicFontLabel, self).__init__(**kwargs)

        self.bind(size=self.on_size)

    def on_size(self, widget, size):
        #print(self.font_size, self.size)
        self.font_size = self.size[0] / 40


class DynamicFontButton(Button):

    iLenOfText = 0

    def __init__(self, **kwargs):
        super(DynamicFontButton, self).__init__(**kwargs)

        self.bind(size=self.on_size)

    def on_size(self, widget, size):
        #if self.iLenOfText > 15:
        #    self.font_size = self.size[0] / 8
        #else:
        self.font_size = self.size[1] / 3

    def on_text(self, widget, text):
        self.iLenOfText = len(text)


class DigitalInput(TextInput):

    def __init__(self, **kwargs):
        super(DigitalInput, self).__init__(**kwargs)

        self.bind(size=self.on_size)

    pat = re.compile('[^0-9]')

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        s = re.sub(pat, '', substring)
        return super(DigitalInput, self).insert_text(s, from_undo=from_undo)

    def on_size(self, widget, size):
        self.font_size = self.size[1] / 2


################
# Главный экран
################


class MainScreen(Screen):

    bExit = DynamicFontButton(text='Exit',
                              size_hint=(.08, .08),
                              pos_hint={'center_x': .93, 'center_y': .95})

    bProtocol = DynamicFontButton(text='Протокол',
                                  size_hint=(.15, .08),
                                  pos_hint={'center_x': .8, 'center_y': .95})

    lCaption_1 = DynamicFontLabel(pos_hint={'center_x': .25, 'center_y': .15},
                                  text='Колонка 1')

    lCaption_2 = DynamicFontLabel(pos_hint={'center_x': .75, 'center_y': .15},
                                  text='Колонка 2')

    iDispenser_1 = Image(source='benzokolonka.gif',
                         pos_hint={'center_x': .375, 'center_y': .625})

    iDispenser_2 = Image(source='benzokolonka.gif',
                         pos_hint={'center_x': .875, 'center_y': .625})

    bFuel_98_1 = DynamicFontButton(pos_hint={'x': .125, 'y': .700},
                                   size_hint=(.1, .1),
                                   text='98')

    bFuel_95_1 = DynamicFontButton(pos_hint={'x': .125, 'y': .600},
                                   size_hint=(.1, .1),
                                   text='95')

    bFuel_92_1 = DynamicFontButton(pos_hint={'x': .125, 'y': .500},
                                   size_hint=(.1, .1),
                                   text='92')

    bFuel_DT_1 = DynamicFontButton(pos_hint={'x': .125, 'y': .400},
                                   size_hint=(.1, .1),
                                   text='ДТ')

    bFuel_98_2 = DynamicFontButton(pos_hint={'x': .625, 'y': .700},
                                   size_hint=(.1, .1),
                                   text='98')

    bFuel_95_2 = DynamicFontButton(pos_hint={'x': .625, 'y': .600},
                                   size_hint=(.1, .1),
                                   text='95')

    bFuel_92_2 = DynamicFontButton(pos_hint={'x': .625, 'y': .500},
                                   size_hint=(.1, .1),
                                   text='92')

    bFuel_DT_2 = DynamicFontButton(pos_hint={'x': .625, 'y': .400},
                                   size_hint=(.1, .1),
                                   text='ДТ')

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

        self.bExit.bind(on_press=self.on_press_exit)
        self.add_widget(self.bExit)

        self.bProtocol.bind(on_press=self.on_press_protocol)
        self.add_widget(self.bProtocol)

        self.add_widget(self.lCaption_1)
        self.add_widget(self.lCaption_2)

        self.add_widget(self.iDispenser_1)
        self.add_widget(self.iDispenser_2)

        self.bFuel_98_1.bind(on_press=self.on_press_98_1)
        self.add_widget(self.bFuel_98_1)

        self.bFuel_95_1.bind(on_press=self.on_press_95_1)
        self.add_widget(self.bFuel_95_1)

        self.bFuel_92_1.bind(on_press=self.on_press_92_1)
        self.add_widget(self.bFuel_92_1)

        self.bFuel_DT_1.bind(on_press=self.on_press_dt_1)
        self.add_widget(self.bFuel_DT_1)

        self.bFuel_98_2.bind(on_press=self.on_press_98_2)
        self.add_widget(self.bFuel_98_2)

        self.bFuel_95_2.bind(on_press=self.on_press_95_2)
        self.add_widget(self.bFuel_95_2)

        self.bFuel_92_2.bind(on_press=self.on_press_92_2)
        self.add_widget(self.bFuel_92_2)

        self.bFuel_DT_2.bind(on_press=self.on_press_dt_2)
        self.add_widget(self.bFuel_DT_2)

    def on_press_98_1(self, instance):
        self.change_fuel(1, '98')
        if f98_1.bBusy:
            sm.current = 'fueling_screen'
        else:
            sm.current = 'info_screen'

    def on_press_95_1(self, instance):
        self.change_fuel(1, '95')
        if f95_1.bBusy:
            sm.current = 'fueling_screen'
        else:
            sm.current = 'info_screen'

    def on_press_92_1(self, instance):
        self.change_fuel(1, '92')
        if f92_1.bBusy:
            sm.current = 'fueling_screen'
        else:
            sm.current = 'info_screen'

    def on_press_dt_1(self, instance):
        self.change_fuel(1, 'dt')
        if fDT_1.bBusy:
            sm.current = 'fueling_screen'
        else:
            sm.current = 'info_screen'

    def on_press_98_2(self, instance):
        self.change_fuel(2, '98')
        if f98_2.bBusy:
            sm.current = 'fueling_screen'
        else:
            sm.current = 'info_screen'

    def on_press_95_2(self, instance):
        self.change_fuel(2, '95')
        if f95_2.bBusy:
            sm.current = 'fueling_screen'
        else:
            sm.current = 'info_screen'

    def on_press_92_2(self, instance):
        self.change_fuel(2, '92')
        if f92_2.bBusy:
            sm.current = 'fueling_screen'
        else:
            sm.current = 'info_screen'

    def on_press_dt_2(self, instance):
        self.change_fuel(2, 'dt')
        if fDT_2.bBusy:
            sm.current = 'fueling_screen'
        else:
            sm.current = 'info_screen'

    @staticmethod
    def on_press_exit(value):
        exit()

    @staticmethod
    def on_press_protocol(value):
        sm.current = 'protocol_screen'

    @staticmethod
    def change_fuel(dispenser=None, ftype=None):
        global fMain
        if dispenser == 1:
            if ftype == '98':
                fMain = f98_1
            elif ftype == '95':
                fMain = f95_1
            elif ftype == '92':
                fMain = f92_1
            elif ftype == 'dt':
                fMain = fDT_1
        elif dispenser == 2:
            if ftype == '98':
                fMain = f98_2
            elif ftype == '95':
                fMain = f95_2
            elif ftype == '92':
                fMain = f92_2
            elif ftype == 'dt':
                fMain = fDT_2
                print(fDT_2.__dict__)

    def on_pre_enter(self, *args):
        Clock.schedule_interval(self.check_busy, 1/2)

    def on_pre_leave(self, *args):
        Clock.unschedule(self.check_busy)

    def check_busy(self, dt):
        if f98_1.bBusy:
            self.bFuel_98_1.background_color = (1, 0, 0, 1)
        elif f98_1.bGun:
            self.bFuel_98_1.background_color = (1, 1, 1, 1)
        else:
            self.bFuel_98_1.background_color = (0, 1, 0, 1)

        if f95_1.bBusy:
            self.bFuel_95_1.background_color = (1, 0, 0, 1)
        elif f95_1.bGun:
            self.bFuel_95_1.background_color = (1, 1, 1, 1)
        else:
            self.bFuel_95_1.background_color = (0, 1, 0, 1)

        if f92_1.bBusy:
            self.bFuel_92_1.background_color = (1, 0, 0, 1)
        elif f92_1.bGun:
            self.bFuel_92_1.background_color = (1, 1, 1, 1)
        else:
            self.bFuel_92_1.background_color = (0, 1, 0, 1)

        if fDT_1.bBusy:
            self.bFuel_DT_1.background_color = (1, 0, 0, 1)
        elif fDT_1.bGun:
            self.bFuel_DT_1.background_color = (1, 1, 1, 1)
        else:
            self.bFuel_DT_1.background_color = (0, 1, 0, 1)

        if f98_2.bBusy:
            self.bFuel_98_2.background_color = (1, 0, 0, 1)
        elif f98_2.bGun:
            self.bFuel_98_2.background_color = (1, 1, 1, 1)
        else:
            self.bFuel_98_2.background_color = (0, 1, 0, 1)

        if f95_2.bBusy:
            self.bFuel_95_2.background_color = (1, 0, 0, 1)
        elif f95_2.bGun:
            self.bFuel_95_2.background_color = (1, 1, 1, 1)
        else:
            self.bFuel_95_2.background_color = (0, 1, 0, 1)

        if f92_2.bBusy:
            self.bFuel_92_2.background_color = (1, 0, 0, 1)
        elif f92_2.bGun:
            self.bFuel_92_2.background_color = (1, 1, 1, 1)
        else:
            self.bFuel_92_2.background_color = (0, 1, 0, 1)

        if fDT_2.bBusy:
            self.bFuel_DT_2.background_color = (1, 0, 0, 1)
        elif fDT_2.bGun:
            self.bFuel_DT_2.background_color = (1, 1, 1, 1)
        else:
            self.bFuel_DT_2.background_color = (0, 1, 0, 1)


##################
# Экран информации
##################


class InfoScreen(Screen):

    lCaption = DynamicFontLabel(text='Caption',
                                pos_hint={'center_x': .5, 'center_y': .9})

    lType = DynamicFontLabel(text='Type',
                             pos_hint={'center_x': .5, 'center_y': .8})

    bGohome = DynamicFontButton(text='Home',
                                size_hint=(.08, .08),
                                pos_hint={'x': .9, 'y': .9})

    lVolume = DynamicFontLabel(text='Резервуар',
                               pos_hint={'center_x': .125, 'center_y': .625})

    pbVolume = ProgressBar(size_hint=(.6, .6),
                           pos_hint={'x': .245, 'y': .325},
                           max=1000,
                           value=750)

    lCapacity = DynamicFontLabel(text='750',
                                 pos_hint={'center_x': .9, 'center_y': .625})

    lNamePrice = DynamicFontLabel(text='Стоимость',
                                  pos_hint={'center_x': .125, 'center_y': .375})

    lPrice = DynamicFontLabel(text='33.54',
                              pos_hint={'center_x': .3, 'center_y': .375})

    bFueling = DynamicFontButton(text='Заправить',
                                 pos_hint={'x': .42, 'y': .15},
                                 size_hint=(.2, .1))

    def __init__(self, **kwargs):
        super(InfoScreen, self).__init__(**kwargs)

        self.add_widget(self.lCaption)

        self.add_widget(self.lType)

        self.bGohome.bind(on_press=self.on_press_gohome)
        self.add_widget(self.bGohome)

        self.add_widget(self.lVolume)

        self.add_widget(self.pbVolume)

        self.add_widget(self.lCapacity)

        self.add_widget(self.lNamePrice)

        self.add_widget(self.lPrice)

        self.bFueling.bind(on_press=self.on_press_fueling)
        self.add_widget(self.bFueling)

    def on_pre_enter(self, *args):
        self.lCaption.text = fMain.sCaption
        self.lType.text = fMain.sType
        self.pbVolume.max = fMain.fMaxVolume
        self.pbVolume.value = fMain.fVolume
        self.lCapacity.text = "%.2f" % fMain.fVolume
        self.lPrice.text = "%.2f" % fMain.fPrice

    @staticmethod
    def on_press_gohome(instance):
        sm.current = 'main_screen'

    @staticmethod
    def on_press_fueling(instance):
        sm.current = 'dose_screen'


####################
# Экран задание дозы
####################


class DoseScreen(Screen):

    lCaption = DynamicFontLabel(text='Caption',
                                pos_hint={'center_x': .5, 'center_y': .9})

    lType = DynamicFontLabel(text='Type',
                             pos_hint={'center_x': .5, 'center_y': .8})

    bGohome = DynamicFontButton(text='Home',
                                size_hint=(.08, .08),
                                pos_hint={'x': .9, 'y': .9})

    lVolume = DynamicFontLabel(text='Литры',
                               pos_hint={'center_x': .125, 'center_y': .625})

    tVolume = DigitalInput(input_type='number',
                           text='0',
                           size_hint=(.08, .05),
                           pos_hint={'x': .245, 'y': .600})

    lPrice = DynamicFontLabel(text='Рубли',
                              pos_hint={'center_x': .125, 'center_y': .375})

    tPrice = DigitalInput(input_type='number',
                          text='0',
                          size_hint=(.08, .05),
                          pos_hint={'x': .245, 'y': .355})

    bGunOn = DynamicFontButton(pos_hint={'x': .42, 'y': .15},
                               size_hint=(.2, .1),
                               text='Снять пистолет')

    bGunOff = DynamicFontButton(pos_hint={'x': .62, 'y': .15},
                                size_hint=(.3, .1),
                                text='Вставить пистолет')

    bFueling = DynamicFontButton(pos_hint={'x': .22, 'y': .15},
                                 size_hint=(.2, .1),
                                 text='Заправить')

    def __init__(self, **kwargs):
        super(DoseScreen, self).__init__(**kwargs)

        self.add_widget(self.lCaption)

        self.add_widget(self.lType)

        self.bGohome.bind(on_press=self.on_press_gohome)
        self.add_widget(self.bGohome)

        self.tVolume.bind(text=self.on_text_volume)
        self.tVolume.bind(focus=self.on_focus_volume)
        self.add_widget(self.tVolume)

        self.add_widget(self.lVolume)

        self.tPrice.bind(text=self.on_text_price)
        self.tPrice.bind(focus=self.on_focus_price)
        self.add_widget(self.tPrice)

        self.add_widget(self.lPrice)

        self.bFueling.bind(on_press=self.on_press_fueling)

        self.bGunOn.bind(on_press=self.on_press_gun_on)

        self.bGunOff.bind(on_press=self.on_press_gun_off)

    def on_pre_enter(self, *args):
        self.lCaption.text = fMain.sCaption
        self.lType.text = fMain.sType
        self.tVolume.text = '0'
        self.tPrice.text = '0'

        if fMain.bGun:
            self.add_widget(self.bGunOff)
            self.add_widget(self.bFueling)
        else:
            self.add_widget(self.bGunOn)

    def on_pre_leave(self, *args):
        self.remove_widget(self.bGunOff)
        self.remove_widget(self.bFueling)
        self.remove_widget(self.bGunOn)

    @staticmethod
    def on_press_gohome(instance):
        sm.current = 'main_screen'

    def on_text_volume(self, instance, value):
        self.tVolume.text = self.tVolume.text[:3]

    def on_text_price(self, instance, value):
        self.tPrice.text = self.tPrice.text[:9]
        if self.tPrice.text != '' and float(self.tPrice.text) / fMain.fPrice > 999  :
            self.tPrice.text = str(fMain.fPrice * 999)

    def on_focus_volume(self, instance, value):
        if self.tVolume.text == '0':
            self.tVolume.text = ''
        if self.tVolume.text != '':
            self.tPrice.text = str('%.2f' % (float(self.tVolume.text) * fMain.fPrice))
        else:
            self.tPrice.text = ''

    def on_focus_price(self, instance, value):
        if self.tPrice.text == '0':
            self.tPrice.text = ''
        if self.tPrice.text != '':
            self.tVolume.text = str('%.2f' % (float(self.tPrice.text) / fMain.fPrice))
        else:
            self.tVolume.text = ''

    def on_press_gun_on(self, value):
        fMain.bGun = True
        self.remove_widget(self.bGunOn)
        self.add_widget(self.bGunOff)
        self.add_widget(self.bFueling)

    def on_press_gun_off(self, value):
        fMain.bGun = False
        self.remove_widget(self.bFueling)
        self.remove_widget(self.bGunOff)
        self.add_widget(self.bGunOn)

    def on_press_fueling(self, value):
        if self.tVolume.text != '' and 0 < float(self.tVolume.text) <= fMain.fVolume:
            fMain.fCapacity = float(self.tVolume.text)
            fMain.iPercent = 0
            fMain.fVolume -= fMain.fCapacity
            fMain.iStatus = 3
            Clock.schedule_interval(fMain.Fueling, 1 / (0.83 / (fMain.fCapacity / 100)))
            sm.current = 'fueling_screen'

        elif self.tVolume.text == '' or float(self.tVolume.text) <= 0:
            popup = Popup(title='Ошибка',
                          content=Label(text='Не задана доза!'),
                          size_hint=(.5, .5))
            popup.open()

        elif fMain.fVolume < float(self.tVolume.text):
            popup = Popup(title='Ошибка',
                          content=Label(text='Недостаточно топлива в резервуаре!'),
                          size_hint=(.5, .5))
            popup.open()


################
# Экран заправки
################


class FuelingScreen(Screen):

    lCaption = DynamicFontLabel(text='Caption',
                                pos_hint={'center_x': .5, 'center_y': .9})

    lType = DynamicFontLabel(text='Type',
                             pos_hint={'center_x': .5, 'center_y': .8})

    bGohome = DynamicFontButton(text='Home',
                                size_hint=(.08, .08),
                                pos_hint={'x': .9, 'y': .9})

    lComplete = DynamicFontLabel(text='Выполнено: ',
                                 pos_hint={'center_x': .125, 'center_y': .425})

    pbComplete = ProgressBar(size_hint=(.6, .6),
                             pos_hint={'center_x': .545, 'center_y': .425},
                             max=100,
                             value=0)

    lPercent = DynamicFontLabel(text='0%',
                                pos_hint={'center_x': .9, 'center_y': .425})

    def __init__(self, **kwargs):
        super(FuelingScreen, self).__init__(**kwargs)

        self.add_widget(self.lCaption)

        self.add_widget(self.lType)

        self.bGohome.bind(on_press=self.on_press_gohome)
        self.add_widget(self.bGohome)

        self.add_widget(self.lComplete)

        self.add_widget(self.pbComplete)

        self.add_widget(self.lPercent)

    def on_pre_enter(self, *args):
        self.lCaption.text = fMain.sCaption
        self.lType.text = fMain.sType
        if fMain.bBusy and fMain.iStatus != 3:
            self.pbComplete.value = fMain.iPercent
            self.lPercent.text = str('{0} %'.format(fMain.iPercent))
            self.lComplete.text = str('{0} / {1}'.format(((fMain.iPercent / 100.) * fMain.fCapacity),
                                                     fMain.fCapacity))
        else:
            Clock.schedule_interval(self.update_info, 1 / (0.83 / (fMain.fCapacity / 100)))
            fMain.bBusy = True

    @staticmethod
    def on_press_gohome(value):
        sm.current = 'main_screen'

    def update_info(self, dt):
        self.pbComplete.value = fMain.iPercent
        self.lPercent.text = str('{0} %'.format(fMain.iPercent))
        self.lComplete.text = str('{0} / {1}'.format(((fMain.iPercent / 100.) * fMain.fCapacity),
                                                     fMain.fCapacity))
        if fMain.iPercent >= 99:
            self.lPercent.text = '100 %'
            self.lComplete.text = str('{0} / {1}'.format(fMain.fCapacity, fMain.fCapacity))
            #print('END!')
            return False


#################################
# Экран обмена сообщениями с ТРК
#################################


class ProtocolScreen(Screen):

    bGohome = DynamicFontButton(text='Home',
                                size_hint=(.08, .08),
                                pos_hint={'x': .9, 'y': .9})

    spAction = Spinner(text='Опрос состояния',
                       values=('Опрос состояния',
                       'Загрузка дозы',
                       'Возврат дозы',
                       'Пуск',
                       'Останов',
                       'Сброс',
                       'Общий останов',
                       'Загрузка параметров',
                       'До полного бака'),
                       size_hint=(None, None),
                       size=(200, 45),
                       pos_hint={'center_x': .2, 'center_y': .9})

    bSend = DynamicFontButton(text='Отправить\редактировать\n запрос',
                              halign='center',
                              valign='middle',
                              size_hint=(None, None),
                              size=(200, 45),
                              pos_hint={'center_x': .2, 'center_y': .7})

    lCapRequest = DynamicFontLabel(text='Запрос: ',
                                   pos_hint={'center_x': .4, 'center_y': .8})

    lCapResponse = DynamicFontLabel(text='Ответ: ',
                                    pos_hint={'center_x': .4, 'center_y': .4})

    lRequest = DynamicFontLabel(text='Request',
                                pos_hint={'center_x': .65, 'center_y': .7})

    lResponse = DynamicFontLabel(text='Response',
                                 pos_hint={'center_x': .65, 'center_y': .3})

    bClear = DynamicFontButton(text='Очистить',
                               size_hint=(None, None),
                               size=(200, 45),
                               pos_hint={'center_x': .2, 'center_y': .1})

    def __init__(self, **kwargs):
        super(ProtocolScreen, self).__init__(**kwargs)

        self.bGohome.bind(on_press=self.on_press_gohome)
        self.add_widget(self.bGohome)

        self.spAction.bind(text=self.on_text_clear)
        self.add_widget(self.spAction)

        self.bSend.bind(on_press=self.on_press_send)
        self.add_widget(self.bSend)

        self.add_widget(self.lCapRequest)
        self.add_widget(self.lCapResponse)

        self.add_widget(self.lRequest)
        self.add_widget(self.lResponse)

        self.bClear.bind(on_press=self.on_press_clear)
        self.add_widget(self.bClear)

    def on_press_gohome(self, value):
        sm.current = 'main_screen'
        global qAnswer
        global qRequest
        qAnswer = State()
        qRequest = Request()
        self.lResponse.text = 'Response'
        self.lRequest.text = 'Request'

    def on_press_clear(self, value):
        global qAnswer
        global qRequest
        qAnswer = State()
        qRequest = Request()
        self.lResponse.text = 'Response'
        self.lRequest.text = 'Request'

    def on_text_clear(self, widget, text):
        global qAnswer
        global qRequest
        qAnswer = State()
        qRequest = Request()
        self.lResponse.text = 'Response'
        self.lRequest.text = 'Request'

    def change_trk(self, string):
        global qAnswer
        if string == '01':
            qAnswer = f98_1
            return 0
        elif string == '02':
            qAnswer = f95_1
            return 0
        elif string == '03':
            qAnswer = f92_1
            return 0
        elif string == '04':
            qAnswer = fDT_1
            return 0
        elif string == '05':
            qAnswer = f98_2
            return 0
        elif string == '06':
            qAnswer = f95_2
            return 0
        elif string == '07':
            qAnswer = f92_2
            return 0
        elif string == '08':
            qAnswer = fDT_2
            return 0
        elif string == '00':
            return 0
        else:
            return 1

    def info_trk(self):
        qRequest.Command = '4'
        self.change_trk(qRequest.TRK_No)
        self.lRequest.text = qRequest.StateToStr()
        self.lResponse.text = qAnswer.Answer(qRequest.StateToStr())

    def print_response(self):
        self.lRequest.text += '\n' + qRequest.StateToStr()
        self.lResponse.text += '\n' + qAnswer.Answer(qRequest.StateToStr())

    def on_pre_enter(self, *args):
        global qRequest
        global qAnswer
        if qRequest.Command != '0':
            if qRequest.Command == '4':
               self.info_trk()
            if qRequest.Command == '1':
                qRequest.Command = '4'
                self.change_trk(qRequest.TRK_No)
                self.lRequest.text = qRequest.StateToStr()
                self.lResponse.text = qAnswer.Answer(qRequest.StateToStr())
                if qAnswer.Code != '05':
                    self.lRequest.text += '\nНедопустимый статус ТРК'
                else:
                    qRequest.Command = '1'
                    self.print_response()
            if qRequest.Command == '43':
                self.info_trk()
                if qAnswer.Code != '01' and qAnswer.Code != '02' and qAnswer.Code != '07' and qAnswer.Code != '04':
                    self.lRequest.text += '\nНедопустимый статус ТРК'
                elif qAnswer.Volume == '000000':
                    self.lRequest.text += '\nОшибка возврата 0 литров'
                else:
                    qRequest.Command = '7'
                    self.print_response()
            if qRequest.Command == '5':
                self.info_trk()
                if qAnswer.Code != '01' and qAnswer.Code != '04':
                    self.lRequest.text += '\nНедопустимый статус ТРК'
                else:
                    qRequest.Command = '5'
                    self.print_response()
            if qRequest.Command == '6':
                self.info_trk()
                if qAnswer.Code != '03':
                    self.lRequest.text += '\nНедопустимый статус ТРК'
                else:
                    qRequest.Command = '6'
                    self.print_response()
            if qRequest.Command == '7':
                self.change_trk(qRequest.TRK_No)
                self.lRequest.text = qRequest.StateToStr()
                self.lResponse.text = qAnswer.Answer(qRequest.StateToStr())
            if qRequest.Command == '3':
                self.info_trk()
                if qAnswer.Code != '05':
                    self.lRequest.text += '\nНедопустимый статус ТРК'
                else:
                    qRequest.Command = '3'
                    self.print_response()

    def on_press_send(self, value):
        global qRequest
        if qRequest.Command != '0':
            pass
        elif self.spAction.text == 'Загрузка дозы':
            qRequest.Command = '1'
            sm.current = 'edit_request_screen'
        elif self.spAction.text == 'Загрузка параметров':
            qRequest.Command = '3'
            sm.current = 'edit_request_screen'
        elif self.spAction.text == 'Опрос состояния':
            qRequest.Command = '4'
            sm.current = 'edit_request_screen'
        elif self.spAction.text == 'Пуск':
            qRequest.Command = '5'
            sm.current = 'edit_request_screen'
        elif self.spAction.text == 'Останов':
            qRequest.Command = '6'
            sm.current = 'edit_request_screen'
        elif self.spAction.text == 'Сброс':
            qRequest.Command = '7'
            sm.current = 'edit_request_screen'
        elif self.spAction.text == 'До полного бака':
            qRequest.Command = '9'
            sm.current = 'edit_request_screen'
        elif self.spAction.text == 'Возврат дозы':
            qRequest.Command = '43'#Возврат дозы из ТРК
            sm.current = 'edit_request_screen'
        elif self.spAction.text == 'Общий останов':
            qRequest.Command = '6'
            for i in range(1, 9):
                qRequest.TRK_No = '{:02d}'.format(i)
                self.change_trk(qRequest.TRK_No)
                if qAnswer.Code == '03':
                    qAnswer.Answer(qRequest.StateToStr())
            qRequest.TRK_No = '00'
            qRequest.Command = '7'
            self.lRequest.text = qRequest.StateToStr()


#############################################
# Экран редактирования сообщения для отправки
#############################################


class EditRequest(Screen):

    lTrk_no = DynamicFontLabel(text='TRK_No',
                               pos_hint={'center_x': .1, 'center_y': .85})

    lCommand = DynamicFontLabel(text='Command',
                                pos_hint={'center_x': .1, 'center_y': .55})

    lPrice = DynamicFontLabel(text='Price',
                              pos_hint={'center_x': .1, 'center_y': .25})

    lVolume = DynamicFontLabel(text='Volume',
                               pos_hint={'center_x': .6, 'center_y': .85})

    lError = DynamicFontLabel(text='Error',
                              pos_hint={'center_x': .6, 'center_y': .55})

    lCode = DynamicFontLabel(text='Code',
                             pos_hint={'center_x': .6, 'center_y': .25})

    tTrk_no = DigitalInput(text='TRK_No',
                           pos_hint={'center_x': .35, 'center_y': .85},
                           size_hint=(.3, .1),
                           readonly=True)

    tCommand = DigitalInput(text='Command',
                            pos_hint={'center_x': .35, 'center_y': .55},
                            size_hint=(.3, .1),
                            readonly=True)

    tPrice = DigitalInput(text='Price',
                          pos_hint={'center_x': .35, 'center_y': .25},
                          size_hint=(.3, .1),
                          readonly=True)

    tVolume = DigitalInput(text='Volume',
                           pos_hint={'center_x': .8, 'center_y': .85},
                           size_hint=(.3, .1),
                           readonly=True)

    tError = DigitalInput(text='Error',
                          pos_hint={'center_x': .8, 'center_y': .55},
                          size_hint=(.3, .1),
                          readonly=True)

    tCode = DigitalInput(text='Code',
                         pos_hint={'center_x': .8, 'center_y': .25},
                         size_hint=(.3, .1),
                         readonly=True)

    bReady = DynamicFontButton(text='Ok',
                               pos_hint={'center_x': .8, 'center_y': .1},
                               size_hint=(.2, .1))

    def __init__(self, **kwargs):
        super(EditRequest, self).__init__(**kwargs)

        self.add_widget(self.lTrk_no)
        self.add_widget(self.lCommand)
        self.add_widget(self.lPrice)
        self.add_widget(self.lVolume)
        self.add_widget(self.lError)
        self.add_widget(self.lCode)

        self.tTrk_no.bind(text=self.on_text_trk_no)
        self.tTrk_no.bind(focus=self.on_focus)
        self.add_widget(self.tTrk_no)

        self.tCommand.bind(text=self.on_text_command)
        self.tCommand.bind(focus=self.on_focus)
        self.add_widget(self.tCommand)

        self.tPrice.bind(text=self.on_text_price)
        self.tPrice.bind(focus=self.on_focus)
        self.add_widget(self.tPrice)

        self.tVolume.bind(text=self.on_text_volume)
        self.tVolume.bind(focus=self.on_focus)
        self.add_widget(self.tVolume)

        self.tError.bind(text=self.on_text_error)
        self.tError.bind(focus=self.on_focus)
        self.add_widget(self.tError)

        self.tCode.bind(text=self.on_text_code)
        self.tCode.bind(focus=self.on_focus)
        self.add_widget(self.tCode)

        self.bReady.bind(on_press=self.on_press_ready)
        self.add_widget(self.bReady)

    def on_pre_enter(self, *args):
        global qRequest
        self.tTrk_no.readonly = True
        self.tPrice.readonly = True
        self.tVolume.readonly = True
        self.tError.readonly = True
        self.tCode.readonly = True
        self.EditReq(qRequest.Command)

    @staticmethod
    def on_focus(widget, value):
        if widget.text == 'TRK_No' or widget.text == 'Command' or widget.text == 'Volume' or widget.text == 'Error' \
                or widget.text == 'Price' or widget.text == 'Code':
            widget.text = ''

    @staticmethod
    def on_text_trk_no(widget, text):
        widget.text = text[:2]

    @staticmethod
    def on_text_command(widget, text):
        widget.text = text[:4]

    @staticmethod
    def on_text_price(widget, text):
        widget.text = text[:9]

    @staticmethod
    def on_text_volume(widget, text):
        widget.text = text[:6]

    @staticmethod
    def on_text_error(widget, text):
        widget.text = text[:2]

    @staticmethod
    def on_text_code(widget, text):
        widget.text = text[:2]

    def on_press_ready(self, value):
        global qRequest
        if self.tTrk_no.text != '' and self.tPrice.text != '' and self.tVolume != ''\
                and self.tError != '' and self.tCode != '':
            qRequest.TRK_No = '{:02d}'.format(int(self.tTrk_no.text))
            qRequest.Price = '{:09d}'.format(int(self.tPrice.text))
            qRequest.Volume = '{:06d}'.format(int(self.tVolume.text))
            qRequest.Error = '{:02d}'.format(int(self.tError.text))
            qRequest.Code = '{:02d}'.format(int(self.tCode.text))
            sm.current = 'protocol_screen'
        else:
            popup = Popup(title='Ошибка',
            content=Label(text='Не все поля заполнены!'),
            size_hint=(.5, .5))
            popup.open()

    def EditReq(self, command):
        if command == '4' or command == '43':
            self.tTrk_no.readonly = False
            self.tTrk_no.text = '99'
            self.tCommand.text = '4'
            self.tPrice.text = '0'
            self.tVolume.text = '0'
            self.tError.text = '00'
            self.tCode.text = '00'
        elif command == '1':
            self.tTrk_no.readonly = False
            self.tTrk_no.text = '99'
            self.tCommand.text = '1'
            self.tPrice.readonly = False
            self.tPrice.text = '0'
            self.tVolume.readonly = False
            self.tVolume.text = '0'
            self.tError.text = '00'
            self.tCode.text = '00'
        elif command == '5':
            self.tTrk_no.readonly = False
            self.tTrk_no.text = '99'
            self.tCommand.text = '5'
            self.tPrice.text = '0'
            self.tVolume.text = '0'
            self.tError.text = '00'
            self.tCode.text = '00'
        elif command == '6':
            self.tTrk_no.readonly = False
            self.tTrk_no.text = '99'
            self.tCommand.text = '6'
            self.tPrice.text = '0'
            self.tVolume.text = '0'
            self.tError.text = '00'
            self.tCode.text = '00'
        elif command == '7':
            self.tTrk_no.readonly = False
            self.tTrk_no.text = '99'
            self.tCommand.text = '7'
            self.tPrice.text = '0'
            self.tVolume.text = '0'
            self.tError.text = '00'
            self.tCode.text = '00'
        elif command == '3':
            self.tTrk_no.readonly = False
            self.tTrk_no.text = '99'
            self.tCommand.text = '3'
            self.tPrice.text = '0'
            self.tVolume.text = '0'
            self.tError.readonly = False
            self.tError.text = '0'
            self.tCode.readonly = False
            self.tCode.text = '0'
        elif command == '9':
            self.tTrk_no.readonly = False
            self.tTrk_no.text = '99'
            self.tCommand.text = '9'
            self.tPrice.text = '0'
            self.tVolume.text = '0'
            self.tError.text = '00'
            self.tCode.text = '00'

##################
# Создание экранов
##################

sm = ScreenManager(transition=NoTransition())
sm.add_widget(MainScreen(name='main_screen'))
sm.add_widget(InfoScreen(name='info_screen'))
sm.add_widget(DoseScreen(name='dose_screen'))
sm.add_widget(FuelingScreen(name='fueling_screen'))
sm.add_widget(ProtocolScreen(name='protocol_screen'))
sm.add_widget(EditRequest(name='edit_request_screen'))
sm.current = 'main_screen'


class TRKApp(App):

    def build(self):
        return sm

if __name__ == '__main__':
    TRKApp().run()