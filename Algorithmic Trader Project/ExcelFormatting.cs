using System;
using Excel = Microsoft.Office.Interop.Excel;

namespace Excel_Interop
{
    public class ExcelFormatting
    {
        public static void ExcelRun(String filename, String wks)
        {
            object m = Type.Missing;

            Excel.Application excelApp = new Excel.Application();
            excelApp.Visible = false;
            excelApp.DisplayAlerts = false;

            Excel.Workbooks xlWorkbooks = excelApp.Workbooks;
            Excel.Workbook xlWorkbook = xlWorkbooks.Open(filename);
            Excel.Worksheet xlWorksheet = (Excel.Worksheet)xlWorkbook.Worksheets[wks];

            xlWorksheet.Columns.AutoFit();
            xlWorksheet.Rows.AutoFit();

            xlWorkbook.Close(SaveChanges: true, Filename: filename);
            excelApp.Quit();

            GC.Collect();
            GC.WaitForPendingFinalizers();

            xlWorkbooks = null;
            xlWorkbook = null;
            xlWorksheet = null;
            excelApp = null;
        }

        public static void Main(String[] args)
        {
            String filename = args[0];
            String wks = args[1];
            ExcelRun(filename, wks);
        }
    }
}
