import csv
import os
from pyexcelerate import Workbook
import openpyxl
import pandas as pd
import re
import glob

# I want to make this dynamic so I don't have to keep hardcoding file names and changing it every time i do a new system
if __name__ == "__main__":
    # only change that is needed is to edit the target directory
    cwd = os.getcwd()
    target_directory = 'Ferro_third_sys_size'

    if len(next(os.walk(target_directory))[1]) == 0:
        system_sizes = ['Base']
    else:
        system_sizes = next(os.walk(target_directory))[1]

    for system_size in system_sizes:
        excel_wb_title = f"{system_size} {target_directory} Python.xlsx"
        print(excel_wb_title)

        # this gets all the .heat files in the directory
        if len(system_sizes) > 1:
            files = glob.glob(fr'{cwd}\\{target_directory}\\{system_size}\*.heat')
        else:
            files = glob.glob(fr'{cwd}\\{target_directory}\*.heat')

        wb = Workbook()
        for file in files:
            row = 0
            filename = file.split('\\')[-1]

            temp_string = re.search('.*_(.*k).*.heat', filename).group(1)
            wks_title = temp_string

            data = []

            with open(file, 'r') as f:
                reader = csv.reader(f)
                for position, row in enumerate(reader):
                    if position > 2:
                        listrow = row[0]
                        listrow = list(listrow.split(" "))
                        listrow = list(filter(None, listrow))
                        listrow = map(float, listrow)
                        data.append(listrow)

            wb.new_sheet(wks_title, data=data)
            wb.save(excel_wb_title)
            print(wks_title)

        #################################################################################################
        xl = pd.ExcelFile(excel_wb_title)
        sheet_names = xl.sheet_names
        print(sheet_names)
        xl.close()

        wb = openpyxl.load_workbook(excel_wb_title)
        for sheet in sheet_names:
            ws = wb[sheet]
            count = 1

            # this is for the formulas
            for i, cellObj in enumerate(ws['I'], 2):
                if i > 21:
                    break

                startingmaxrow = (ws.max_row - 20) + i

                startingirow = 0 + i

                cell = 'H{}'.format(startingirow)
                icell = 'G{}'.format(startingirow)
                formula = f"=AVERAGE(IF(MOD(_xlfn.ROW(D{startingirow}:D{startingmaxrow})-(A{startingirow}+1)," \
                          f"21)=0,D{startingirow}:D{startingmaxrow}))"

                ws[cell] = formula
                ws[icell] = count
                ws.formula_attributes[cell] = {'t': 'array', 'ref': f"{cell}:{cell}"}
                count += 1

            print(ws.max_row)
            print(sheet)

            xvalues = openpyxl.chart.Reference(ws, min_col=7, min_row=2, max_col=7, max_row=21)
            yvalues = openpyxl.chart.Reference(ws, min_col=8, min_row=2, max_col=8, max_row=21)

            chart = openpyxl.chart.scatter_chart.ScatterChart()
            series = openpyxl.chart.Series(yvalues, xvalues)
            series.marker = openpyxl.chart.marker.Marker('circle')
            series.graphicalProperties.line.noFill = True
            chart.series.append(series)
            chart.title = "1-20"
            ws.add_chart(chart, "J3")

            xvalues1 = openpyxl.chart.Reference(ws, min_col=7, min_row=3, max_col=7, max_row=10)
            yvalues1 = openpyxl.chart.Reference(ws, min_col=8, min_row=3, max_col=8, max_row=10)

            chart = openpyxl.chart.scatter_chart.ScatterChart()
            series = openpyxl.chart.Series(yvalues1, xvalues1)
            series.marker = openpyxl.chart.marker.Marker('circle')
            series.graphicalProperties.line.noFill = True
            chart.series.append(series)
            chart.title = "2-9"
            series.trendline = openpyxl.chart.trendline.Trendline(dispEq=True, dispRSqr=True, trendlineType="linear")
            ws.add_chart(chart, "J19")

            xvalues1 = openpyxl.chart.Reference(ws, min_col=7, min_row=12, max_col=7, max_row=20)
            yvalues1 = openpyxl.chart.Reference(ws, min_col=8, min_row=12, max_col=8, max_row=20)

            chart = openpyxl.chart.scatter_chart.ScatterChart()
            series = openpyxl.chart.Series(yvalues1, xvalues1)
            series.marker = openpyxl.chart.marker.Marker('circle')
            series.graphicalProperties.line.noFill = True
            chart.series.append(series)
            chart.title = "11-19"
            series.trendline = openpyxl.chart.trendline.Trendline(dispEq=True, dispRSqr=True, trendlineType="linear")
            ws.add_chart(chart, "J35")

            # slopes of 2-9 and 11-19
            formula = f"=ABS(LINEST(H3:H10))"

            cell = 'G24'
            ws[cell] = formula
            ws.formula_attributes[cell] = {'t': 'array', 'ref': f"{cell}:{cell}"}

            formula = f"=ABS(LINEST(H12:H20))"

            cell = 'G25'
            ws[cell] = formula
            ws.formula_attributes[cell] = {'t': 'array', 'ref': f"{cell}:{cell}"}

        wb.save(excel_wb_title)
        wb.close()
