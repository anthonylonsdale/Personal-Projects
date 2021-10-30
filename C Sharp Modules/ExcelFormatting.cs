using System;
using Excel = Microsoft.Office.Interop.Excel;


namespace Excel_Interop
{
    public class ExcelFormatting
    {
        public static void ExcelRun(String filename)
        {
            Excel.Application excelApp = new Excel.Application
            {
                Visible = false,
                DisplayAlerts = false
            };

            Excel.Workbooks xlWorkbooks = excelApp.Workbooks;
            Excel.Workbook xlWorkbook = xlWorkbooks.Open(filename);

            foreach ( Excel.Worksheet worksheet in xlWorkbook.Worksheets )
            {
                worksheet.Columns.AutoFit();
                worksheet.Rows.AutoFit();
            }

            
            xlWorkbook.Close(SaveChanges: true, Filename: filename);
            excelApp.Quit();

            GC.Collect();
            GC.WaitForPendingFinalizers();

            System.Runtime.InteropServices.Marshal.FinalReleaseComObject(xlWorkbooks);
            System.Runtime.InteropServices.Marshal.FinalReleaseComObject(xlWorkbook);
            System.Runtime.InteropServices.Marshal.FinalReleaseComObject(excelApp);
        }

        public static void Main(String args)
        {
            String filename = args;
            ExcelRun(filename);
        }
    }
}
