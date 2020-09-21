import xlrd
import pandas as pd
import time
from twilio.rest import Client


def numbers():
    loc = 'Twilio Text File.xlsx'
    xl = pd.ExcelFile(loc)
    for element in xl.sheet_names:
        wb = xlrd.open_workbook(loc)
        sheet = wb.sheet_by_name(element)
        if element == 'Outbound':
            for k in range(sheet.nrows):
                number = str(sheet.cell_value(k, 0))
                outbound_number_list.append(number)
        if element == 'Inbound':
            for h in range(sheet.nrows):
                number = str(sheet.cell_value(h, 0))
                inbound_number_list.append(number)


def chunks(list, n):
    return [list[i:i+n] for i in range(0, len(list), n)]


if __name__ == '__main__':
    inbound_number_list = []
    outbound_number_list = []
    numbers()
    inbound_nested_list = chunks(inbound_number_list, 935)

    account_sid = '--------------------------------'
    auth_token = '--------------------------------'
    client = Client(account_sid, auth_token)
    for j in range(37, 37):
        for i in range(len(inbound_nested_list[j])):
            if i % 35 == 0:
                time.sleep(5)
            receiving_number = str(inbound_nested_list[j][i])
            sending_number = str(outbound_number_list[i % 35])
            message = client.messages.create(body="Thank you, Clay County Voters, for taking the time to review my "
                                                  "qualifications. Your vote is valued and appreciated. It's time that "
                                                  "residents have assessments that are fair and accurate. Thank you for"
                                                  " your vote, CHRIS LONSDALE!",
                                             from_=sending_number, to=receiving_number)
            print(message.sid)
