package com.company;

import io.github.mainstringargs.alpaca.AlpacaAPI;
import io.github.mainstringargs.alpaca.enums.ActivityType;
import io.github.mainstringargs.alpaca.enums.Direction;
import io.github.mainstringargs.alpaca.rest.exception.AlpacaAPIRequestException;
import io.github.mainstringargs.domain.alpaca.accountactivities.AccountActivity;
import io.github.mainstringargs.domain.alpaca.accountactivities.NonTradeActivity;
import io.github.mainstringargs.domain.alpaca.accountactivities.TradeActivity;

import com.gembox.spreadsheet.*;
import com.gembox.spreadsheet.conditionalformatting.*;

import java.time.ZoneId;
import java.time.ZonedDateTime;

import java.io.File;
import java.io.IOException;
import java.io.FileOutputStream;

import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.List;

import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.DataFormat;
import org.apache.poi.xssf.usermodel.XSSFRow;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.apache.poi.ss.util.CellUtil;


public class Main {
    public static void main(String[] args) throws Exception {
        AlpacaAPI alpacaAPI = new AlpacaAPI();

        System.out.println("\n\nAccount Information:");
        System.out.println("\t" + alpacaAPI.getAccount().toString().replace(",", ",\n\t"));

        try {
            List<AccountActivity> accountActivities = alpacaAPI.getAccountActivities(null, null,
                    ZonedDateTime.of(2021, 1, 6, 0, 0, 0, 0,
                            ZoneId.of("America/New_York")), Direction.ASCENDING,
                    null, null, (ActivityType[]) null);
            System.out.println("Trade Activity:");
            for (AccountActivity accountActivity : accountActivities) {
                if (accountActivity instanceof TradeActivity) {
                    System.out.println(accountActivity);
                }
                else if (accountActivity instanceof NonTradeActivity) {
                    System.out.println("Non-Trade Activity: " + accountActivity);
                }
            }
        }
        catch (AlpacaAPIRequestException e) {
            e.printStackTrace();
        }
        // Performance Summary exported to an excel workbook
        Excel();
    }

    public static void Excel() throws IOException
    {
        XSSFWorkbook workbook = new XSSFWorkbook();
        DataFormat dataFormat = workbook.createDataFormat();
        XSSFSheet spreadsheet = workbook.createSheet("Portfolio Performance");
        XSSFRow row;

        Map < String, Object[] > empinfo = new TreeMap<>();
        // repeat this line as much as necessary for each row
        empinfo.put("1", new Object[] {
                "", "All Trades", "Long Trades", "Short Trades"});
        empinfo.put("2", new Object[] {
                "Total Net Profit"});

        Set < String > keyid = empinfo.keySet();
        int rowid = 0;

        for (String key : keyid) {
            row = spreadsheet.createRow(rowid++);
            Object[] objectArr = empinfo.get(key);
            int cellid = 0;

            for (Object obj: objectArr) {
                Cell cell = row.createCell(cellid++);
                cell.setCellValue((String)obj);
            }
        }
        try (FileOutputStream outputStream = new FileOutputStream("Alpaca Portfolio.xlsx")) {
            workbook.write(outputStream);
        }

        System.out.println("Portfolio Metrics Written Successfully @ C:\\Users\\fabio\\OneDrive\\Documents\\Algo " +
                "Trader Experimental Project");
    }
}
