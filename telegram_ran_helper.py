#!/usr/bin/python3
# -*- coding: utf-8 -*-
import re
import logging
import math
from ipcalc import Network
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, Filters, Updater
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y.%m.%d %I:%M:%S %p', level=logging.DEBUG)


# contains icq bot work code. Vitrina code: 739b2096-3845-4283-ad0f-31c75b4a5745

# =============================================================================
# start bot


class FormulaTg(object):
    def __init__(self, tg_token):
        self.updater = None
        self.start_dispatchers(tg_token)
        print("TG bot started!", self.updater)

    # =============================================================================
    # start bot
    def start_dispatchers(self, bot_token):
        self.updater = Updater(token=bot_token, use_context=True)
        self.updater.dispatcher.add_handler(CommandHandler('start', self.send_welcome_message))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.cb_get_message))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.cb_opt_button))
        self.updater.start_polling()

    # =============================================================================
    # Text message handler

    def send_welcome_message(self, upd: Update, context: CallbackContext):
        if upd.message.from_user.language_code == "ru":
            message_text = (
                "Я бот-помощник радионинженера. Я умею вычислять частоты по номеру радиоканала, "
                "переводить ДБм в Ватты и обратно, вычислять enodeb по ECI, расписывать IP-сети.\n"
                "Отправьте мне целое число, и я предложу вам варианты его конвертации!\n"
                "Отправьте мне IP-адрес с маской (в формате 'x.x.x.x/n'), и я распишу вам подсеть!\n"
                "Если вы добавили меня в группу, я буду реагировать только на прямые сообщения через '@'."
            )
        else:
            message_text = (
                "I am a RAN engineer helper bot! I can calculate frequencies from channel numbers, "
                "convert dBm to watts and vice versa, calculate eNodeB from ECI, and describe IP networks!\n"
                "Just send me an integer number or an IP network (in the format 'x.x.x.x/n'), and I will provide you with options for conversion!\n"
                "If you add me to a group, I will only respond to direct messages addressed to me with '@'."
            )
        context.bot.send_message(chat_id=upd.effective_chat.id, text=message_text)

    def cb_get_message(self, upd: Update, context: CallbackContext):
        Thread(target=self.tr_get_message, args=(upd, context)).start()
        Thread(target=self.conf.tg_get_user_feedback, args=("tg_gsm", upd.effective_chat.id, upd.effective_user.id,
                                                            upd.effective_message.text)).start()

    def tr_get_message(self, upd: Update, context: CallbackContext):
        text = upd.message.text
        chatId = upd.message.chat.id
        if len(re.findall(r"\d", text)) and not len(re.findall(r"\D", text)):
            buttons = self.get_fm_options_button()
            context.bot.send_message(chat_id=chatId, text=text, reply_markup=buttons)
        elif len(re.findall(r"\d+\.\d+\.\d+\.\d+/\d+|\d+\.\d+\.\d+\.\d+", text)):
            ip = re.findall(r"\d+\.\d+\.\d+\.\d+/\d+|\d+\.\d+\.\d+\.\d+", text)
            text = self.ip_formula_processing(ip[0])
            context.bot.send_message(chat_id=chatId, text=text, reply_markup=self.get_ip_options_button())
        else:
            pass

    @staticmethod
    def get_fm_options_button(opt="none"):
        button = [
            [InlineKeyboardButton(text=("✅" if opt == "2gF" else "") + "arfcn > Mhz", callback_data='2gF'),
             InlineKeyboardButton(text=("✅" if opt == "3gF" else "") + "uarfcn > Mhz", callback_data='3gF'),
             InlineKeyboardButton(text=("✅" if opt == "4gF" else "") + "earfcn > Mhz", callback_data='4gF'),
             InlineKeyboardButton(text=("✅" if opt == "5gF" else "") + "nrarfcn > Mhz", callback_data='5gF'),
             ],
            [InlineKeyboardButton(text=("✅" if opt == "DbmW" else "") + "Dbm > Watt", callback_data='DbmW'),
             InlineKeyboardButton(text=("✅" if opt == "WDbm" else "") + "Watt > Dbm", callback_data='WDbm'),
             InlineKeyboardButton(text=("✅" if opt == "ECI" else "") + "ECI(dec) > enbid", callback_data='ECI'),
             InlineKeyboardButton(text=("✅" if opt == "ECGI" else "") + "ECGI > PLMN+ECI", callback_data='ECGI'),
             ],
        ]
        return InlineKeyboardMarkup(button)

    @staticmethod
    def get_ip_options_button():
        button = [
            [InlineKeyboardButton(text="+bitmask", callback_data='IP_up'),
             InlineKeyboardButton(text="-bitmask", callback_data='IP_down'),
             ]]
        return InlineKeyboardMarkup(button)

    # =============================================================================
    # button handler
    def cb_opt_button(self, upd: Update, context: CallbackContext):
        Thread(target=self.tr_opt_button, args=(upd, context)).start()

    def tr_opt_button(self, upd: Update, context: CallbackContext):
        query = upd.callback_query
        query.answer()
        msg_id = query.message.message_id
        msg_chat = query.message.chat.id
        msg_text = query.message.text
        option = query.data
        if option in (["IP_up", "IP_down"]):
            button = self.get_ip_options_button()
            msg_text = self.ip_formula_processing(msg_text.split(" :")[0], option)
            context.bot.editMessageText(msg_text, msg_chat, msg_id, reply_markup=button)
        else:
            button = self.get_fm_options_button(option)
            msg_text = self.int_formula_processing(msg_text.split(": ")[0], option)
            context.bot.editMessageText(msg_text, msg_chat, msg_id, reply_markup=button)

    @staticmethod
    def convert_ecgi_to_plmn_and_eci(ecgi: int):
        plmn_id = (ecgi >> 28) & 0xFFFFFF  # 24
        eci = ecgi & 0x0FFFFFFF  # 28
        mcc1 = (plmn_id >> 20) & 0xF
        mcc2 = (plmn_id >> 16) & 0xF
        mcc3 = (plmn_id >> 12) & 0xF
        mnc1 = (plmn_id >> 8) & 0xF
        mnc2 = (plmn_id >> 4) & 0xF
        mnc3 = plmn_id & 0xF
        mcc = f"{mcc1}{mcc2}{mcc3}"
        if mnc3 == 0xF:
            mnc = f"{mnc1}{mnc2}"
        else:
            mnc = f"{mnc1}{mnc2}{mnc3}"
        return f"PLMN ID: {mcc}-{mnc}, ECI: {eci}"

    @staticmethod
    def ip_formula_processing(ip, option="default"):
        try:
            if option == "IP_up":
                if int(ip.split("/")[1]) < 32:
                    ip = ip.split("/")[0] + "/" + str(int(ip.split("/")[1]) + 1)
            if option == "IP_down":
                ip = ip.split("/")[0] + "/" + str(int(ip.split("/")[1]) - 1)
            net = Network(ip)
            guess_network = str(net.guess_network())
            netmask = str(net.netmask())
            size = str(net.size() - 2)
            size = "1" if int(size) < 1 else size
            host_minmax = f"\nfirst: {str(net.host_first())} \nlast: {str(net.host_last())}" if int(size) > 1 else ""
            result = f"{str(net.to_ipv4())} :belongs to \nnet {guess_network} \nmask {netmask}" \
                     f"\nthere are {size} hosts" + host_minmax
            return result
        except Exception as e:
            return ip + " :Error! Check input value: " + str(e)

    def int_formula_processing(self, text, option):
        result = " Undefined option: " + option
        if option == "test":
            result = "test_value"
        elif option == "2gF":
            result = " arfcn out of range " + option
            for key in self.ARFCN.keys():
                if int(key.split("-")[0]) < int(text) < int(key.split("-")[-1]):
                    band = self.ARFCN[key]['band']
                    F_ul = self.ARFCN[key]['F_ul']
                    F_delta = self.ARFCN[key]['F_delta']
                    N_offset = self.ARFCN[key]['N_offset']
                    freq_UL = str(float(F_ul) + 0.2 * (int(text) - int(N_offset)))
                    freq_DL = str(float(freq_UL) + float(F_delta))
                    result = band + ": 🔽 " + freq_DL + " - " + freq_UL + " 🔼 MHz"
                    break
        elif option == "3gF":
            resultDL = resultUL = ""
            for key in self.UARFCN_DL.keys():
                if int(key.split("-")[0]) < int(text) < int(key.split("-")[-1]):
                    band = self.UARFCN_DL[key]['band']
                    direct = self.UARFCN_DL[key]['direct']
                    offset = int(self.UARFCN_DL[key]['offset'])
                    freq = str(int(text) / 5 + offset)
                    resultDL = "band " + band + " (" + direct + "), " + freq + "Mhz"
                    break
            for key in self.UARFCN_UL.keys():
                if int(key.split("-")[0]) < int(text) < int(key.split("-")[-1]):
                    band = self.UARFCN_UL[key]['band']
                    direct = self.UARFCN_UL[key]['direct']
                    offset = int(self.UARFCN_UL[key]['offset'])
                    freq = str(int(text) / 5 + offset)
                    resultUL = "band " + band + " (" + direct + "), " + freq + "Mhz"
                    break
            if resultDL == "" and resultUL == "":
                result = " uarfcn out of range " + option
            else:
                result = "; ".join([resultDL, resultUL])
        elif option == "4gF":
            result = " earfcn out of range " + option
            for key in self.EARFCN.keys():
                if int(key.split("-")[0]) < int(text) < int(key.split("-")[-1]):
                    f_low = int(self.EARFCN[key]['F_low'])
                    num = int(text) - int(self.EARFCN[key]['N_offset'])
                    freq = str(f_low + 0.1 * num)
                    band = self.EARFCN[key]['band']
                    direct = self.EARFCN[key]['direct']
                    result = "band " + band + " (" + direct + "), " + freq + "Mhz"
                    break
        elif option == "5gF":
            result = " nrarfcn out of range " + option
            for key in self.NARFCN.keys():
                if int(key.split("-")[0]) < int(text) < int(key.split("-")[-1]):
                    F_delta = float(self.NARFCN[key]['F_delta'])
                    F_offset = float(self.NARFCN[key]['F_offset'])
                    N_offset = int(self.NARFCN[key]['N_offset'])
                    freq = str(F_offset + F_delta * (int(text) - N_offset))
                    result = freq + " Mhz"
                    break
        elif option == "DbmW":
            try:
                result = str(math.floor(math.pow(10, int(text) / 10)) / 1000) + " Watt"
            except Exception as e:
                result = "Error! Check input value: " + str(e)
        elif option == "WDbm":
            try:
                result = str(math.floor(10 * math.log10(1000 * int(text)))) + " Dbm"
            except Exception as e:
                result = "Error! Check input value: " + str(e)
        elif option == "ECI":
            try:
                result = " enbid: " + str(int(text) // 256) + ", cid: " + str(int(text) % 256)
            except Exception as e:
                result = "Error! Check input value: " + str(e)
        elif option == "ECGI":
            try:
                result = convert_ecgi_to_plmn_and_eci(int(text))
            except Exception as e:
                result = "Error! Check input value: " + str(e)
        return text + ": " + result

    NARFCN = {'0-599999': {'F_delta': '0.005', 'F_offset': '0', 'N_offset': '0'},
              '600000-2016666': {'F_delta': '0.015', 'F_offset': '3000', 'N_offset': '600000'},
              '2016667-3279165': {'F_delta': '0.06', 'F_offset': '24250.08', 'N_offset': '2016667'},
              }

    UARFCN_UL = {'10562-10838': {'band': '1', 'direct': 'UL', 'offset': '0', 'F_low': '2112,4', 'F_high': '2167,6'},
                 '9662-9938': {'band': '2', 'direct': 'UL', 'offset': '0', 'F_low': '1932,4', 'F_high': '1987,6'},
                 '7462-7813': {'band': '3', 'direct': 'UL', 'offset': '1575', 'F_low': '1807,4', 'F_high': '1877,6'},
                 '8757-8958': {'band': '4', 'direct': 'UL', 'offset': '1805', 'F_low': '2112,4', 'F_high': '2152,6'},
                 '4357-4458': {'band': '5', 'direct': 'UL', 'offset': '0', 'F_low': '871,4', 'F_high': '891,6'},
                 '4387-4413': {'band': '6', 'direct': 'UL', 'offset': '0', 'F_low': '877,4', 'F_high': '882,6'},
                 '10937-11263': {'band': '7', 'direct': 'UL', 'offset': '2175', 'F_low': '2622,4', 'F_high': '2687,6'},
                 '4297-4448': {'band': '8', 'direct': 'UL', 'offset': '340', 'F_low': '927,4', 'F_high': '957,6'},
                 '9237-9387': {'band': '9', 'direct': 'UL', 'offset': '0', 'F_low': '1847,4', 'F_high': '1877,4'},
                 '9072-9348': {'band': '10', 'direct': 'UL', 'offset': '1490', 'F_low': '2112,4', 'F_high': '2167,6'},
                 }
    UARFCN_DL = {'9612-9888': {'band': '1', 'direct': 'DL', 'offset': '0', 'F_low': '1922,4', 'F_high': '1977,6'},
                 '9262-9538': {'band': '2', 'direct': 'DL', 'offset': '0', 'F_low': '1852,4', 'F_high': '1907,6'},
                 '7037-7388': {'band': '3', 'direct': 'DL', 'offset': '1525', 'F_low': '1712,4', 'F_high': '1782,6'},
                 '7112-7313': {'band': '4', 'direct': 'DL', 'offset': '1450', 'F_low': '1712,4', 'F_high': '1752,6'},
                 '4132-4233': {'band': '5', 'direct': 'DL', 'offset': '0', 'F_low': '826,4', 'F_high': '846,6'},
                 '4162-4188': {'band': '6', 'direct': 'DL', 'offset': '0', 'F_low': '832,4', 'F_high': '837,6'},
                 '10412-10738': {'band': '7', 'direct': 'DL', 'offset': '2100', 'F_low': '2502,4', 'F_high': '2567,6'},
                 '4072-4223': {'band': '8', 'direct': 'DL', 'offset': '340', 'F_low': '882,4', 'F_high': '912,6'},
                 '8762-8912': {'band': '9', 'direct': 'DL', 'offset': '0', 'F_low': '1752,4', 'F_high': '1782,4'},
                 '7427-7703': {'band': '10', 'direct': 'DL', 'offset': '1135', 'F_low': '1712,4', 'F_high': '1767,6'},
                 }
    EARFCN = {'0-599': {'band': '1', 'direct': 'DL', 'F_low': '2110', 'N_offset': '0'},
              '600-1199': {'band': '2', 'direct': 'DL', 'F_low': '1930', 'N_offset': '600'},
              '1200-1949': {'band': '3', 'direct': 'DL', 'F_low': '1805', 'N_offset': '1200'},
              '1950-2399': {'band': '4', 'direct': 'DL', 'F_low': '2110', 'N_offset': '1950'},
              '2400-2649': {'band': '5', 'direct': 'DL', 'F_low': '869', 'N_offset': '2400'},
              '2650-2749': {'band': '6', 'direct': 'DL', 'F_low': '875', 'N_offset': '2650'},
              '2750-3449': {'band': '7', 'direct': 'DL', 'F_low': '2620', 'N_offset': '2750'},
              '3450-3799': {'band': '8', 'direct': 'DL', 'F_low': '925', 'N_offset': '3450'},
              '3800-4149': {'band': '9', 'direct': 'DL', 'F_low': '1844,9', 'N_offset': '3800'},
              '4150-4749': {'band': '10', 'direct': 'DL', 'F_low': '2110', 'N_offset': '4150'},
              '4750-4949': {'band': '11', 'direct': 'DL', 'F_low': '1475,9', 'N_offset': '4750'},
              '5010-5179': {'band': '12', 'direct': 'DL', 'F_low': '729', 'N_offset': '5010'},
              '5180-5279': {'band': '13', 'direct': 'DL', 'F_low': '746', 'N_offset': '5180'},
              '5280-5379': {'band': '14', 'direct': 'DL', 'F_low': '758', 'N_offset': '5280'},
              '5730-5849': {'band': '17', 'direct': 'DL', 'F_low': '734', 'N_offset': '5730'},
              '5850-5999': {'band': '18', 'direct': 'DL', 'F_low': '860', 'N_offset': '5850'},
              '6000-6149': {'band': '19', 'direct': 'DL', 'F_low': '875', 'N_offset': '6000'},
              '6150-6449': {'band': '20', 'direct': 'DL', 'F_low': '791', 'N_offset': '6150'},
              '6450-6599': {'band': '21', 'direct': 'DL', 'F_low': '1495,9', 'N_offset': '6450'},
              '7500-7699': {'band': '23', 'direct': 'DL', 'F_low': '2180', 'N_offset': '7500'},
              '7700-8039': {'band': '24', 'direct': 'DL', 'F_low': '1525', 'N_offset': '7700'},
              '8040-8689': {'band': '25', 'direct': 'DL', 'F_low': '1930', 'N_offset': '8040'},
              '36000-36199': {'band': '33', 'direct': 'DL-UL', 'F_low': '1900', 'N_offset': '36000'},
              '36200-36349': {'band': '34', 'direct': 'DL-UL', 'F_low': '2010', 'N_offset': '36200'},
              '36350-36949': {'band': '35', 'direct': 'DL-UL', 'F_low': '1850', 'N_offset': '36350'},
              '36950-37549': {'band': '36', 'direct': 'DL-UL', 'F_low': '1930', 'N_offset': '36950'},
              '37550-37749': {'band': '37', 'direct': 'DL-UL', 'F_low': '1910', 'N_offset': '37550'},
              '37750-38249': {'band': '38', 'direct': 'DL-UL', 'F_low': '2570', 'N_offset': '37750'},
              '38250-38649': {'band': '39', 'direct': 'DL-UL', 'F_low': '1880', 'N_offset': '38250'},
              '38650-39649': {'band': '40', 'direct': 'DL-UL', 'F_low': '2300', 'N_offset': '38650'},
              '39650-41589': {'band': '41', 'direct': 'DL-UL', 'F_low': '2496', 'N_offset': '39650'},
              '41590-43589': {'band': '42', 'direct': 'DL-UL', 'F_low': '3400', 'N_offset': '41590'},
              '43590-45589': {'band': '43', 'direct': 'DL-UL', 'F_low': '3600', 'N_offset': '43590'},
              '18000-18599': {'band': '1', 'direct': 'UL', 'F_low': '1920', 'N_offset': '18000'},
              '18600-19199': {'band': '2', 'direct': 'UL', 'F_low': '1850', 'N_offset': '18600'},
              '19200-19949': {'band': '3', 'direct': 'UL', 'F_low': '1710', 'N_offset': '19200'},
              '19950-20399': {'band': '4', 'direct': 'UL', 'F_low': '1710', 'N_offset': '19950'},
              '20400-20649': {'band': '5', 'direct': 'UL', 'F_low': '824', 'N_offset': '20400'},
              '20650-20749': {'band': '6', 'direct': 'UL', 'F_low': '830', 'N_offset': '20650'},
              '20750-21449': {'band': '7', 'direct': 'UL', 'F_low': '2500', 'N_offset': '20750'},
              '21450-21799': {'band': '8', 'direct': 'UL', 'F_low': '880', 'N_offset': '21450'},
              '21800-22149': {'band': '9', 'direct': 'UL', 'F_low': '1749,9', 'N_offset': '21800'},
              '22150-22749': {'band': '10', 'direct': 'UL', 'F_low': '1710', 'N_offset': '22150'},
              '22750-22949': {'band': '11', 'direct': 'UL', 'F_low': '1427,9', 'N_offset': '22750'},
              '23010-23179': {'band': '12', 'direct': 'UL', 'F_low': '699', 'N_offset': '23010'},
              '23180-23279': {'band': '13', 'direct': 'UL', 'F_low': '777', 'N_offset': '23180'},
              '23280-23379': {'band': '14', 'direct': 'UL', 'F_low': '788', 'N_offset': '23280'},
              '23730-23849': {'band': '17', 'direct': 'UL', 'F_low': '704', 'N_offset': '23730'},
              '23850-23999': {'band': '18', 'direct': 'UL', 'F_low': '815', 'N_offset': '23850'},
              '24000-24149': {'band': '19', 'direct': 'UL', 'F_low': '830', 'N_offset': '24000'},
              '24150-24449': {'band': '20', 'direct': 'UL', 'F_low': '832', 'N_offset': '24150'},
              '24450-24599': {'band': '21', 'direct': 'UL', 'F_low': '1447,9', 'N_offset': '24450'},
              '25500-25699': {'band': '23', 'direct': 'UL', 'F_low': '2000', 'N_offset': '25500'},
              '25700-26039': {'band': '24', 'direct': 'UL', 'F_low': '1626,5', 'N_offset': '25700'},
              '26040-26689': {'band': '25', 'direct': 'UL', 'F_low': '1850', 'N_offset': '26040'},
              }

    ARFCN = {
        '1-124': {'band': 'P-GSM', 'F_ul': '890', 'N_offset': '0', 'F_delta': '45'},
        '259-293': {'band': 'GSM 450', 'F_ul': '450.6', 'N_offset': '259', 'F_delta': '10'},
        '306-340': {'band': 'GSM 480', 'F_ul': '479', 'N_offset': '306', 'F_delta': '10'},
        '438-511': {'band': 'GSM 750', 'F_ul': '747.2', 'N_offset': '438', 'F_delta': '30'},
        '128-251': {'band': 'GSM 850', 'F_ul': '824.2', 'N_offset': '128', 'F_delta': '45'},
        '975-1023': {'band': 'E-GSM', 'F_ul': '890', 'N_offset': '1024', 'F_delta': '45'},
        '512-885': {'band': 'DCS 1800', 'F_ul': '1710', 'N_offset': '512', 'F_delta': '95'},
        '512-810': {'band': 'PCS 1900', 'F_ul': '1850', 'N_offset': '512', 'F_delta': '80'},
        '955-1023': {'band': 'GSM-R', 'F_ul': '890', 'N_offset': '1024', 'F_delta': '45'},

    }


def main():
    if len(sys.argv) != 2:
        print("Usage: telegram_ran_helper.py <tg_token>")
        sys.exit(1)

    tg_token = sys.argv[1]
    FormulaTg(tg_token)


if __name__ == "__main__":
    main()
