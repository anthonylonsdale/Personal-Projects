package com.company;

import io.github.mainstringargs.alpaca.AlpacaAPI;
import io.github.mainstringargs.alpaca.enums.ActivityType;
import io.github.mainstringargs.alpaca.enums.Direction;
import io.github.mainstringargs.alpaca.enums.PortfolioPeriodUnit;
import io.github.mainstringargs.alpaca.enums.PortfolioTimeFrame;
import io.github.mainstringargs.alpaca.rest.exception.AlpacaAPIRequestException;
import io.github.mainstringargs.domain.alpaca.accountactivities.AccountActivity;
import io.github.mainstringargs.domain.alpaca.accountactivities.NonTradeActivity;
import io.github.mainstringargs.domain.alpaca.accountactivities.TradeActivity;

import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZonedDateTime;

import java.io.IOException;
import java.io.FileOutputStream;

import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.List;

import io.github.mainstringargs.domain.alpaca.portfoliohistory.PortfolioHistory;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.DataFormat;
import org.apache.poi.xssf.usermodel.XSSFRow;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;


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

        try {
            // Get the 'PortfolioHistory' and print out static information
            PortfolioHistory portfolioHistory = alpacaAPI.getPortfolioHistory(
                    3,
                    PortfolioPeriodUnit.DAY,
                    PortfolioTimeFrame.ONE_HOUR,
                    LocalDate.of(2021, 1, 7),
                    false);
            System.out.printf("Timeframe: %s, Base value: %s \n",
                    portfolioHistory.getTimeframe(),
                    portfolioHistory.getBaseValue());

            // Loop through all indices and print the dynamic historical information uniformly
            int historyUnitSize = portfolioHistory.getTimestamp().size();
            for (int historyIndex = 0; historyIndex < historyUnitSize; historyIndex++) {
                System.out.printf("Timestamp: %s, Equity: %s, PnL: %s, PnL%%: %s \n",
                        portfolioHistory.getTimestamp().get(historyIndex),
                        portfolioHistory.getEquity().get(historyIndex),
                        portfolioHistory.getProfitLoss().get(historyIndex),
                        portfolioHistory.getProfitLossPct().get(historyIndex));
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
                "Total Net Profit", });

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

        for (int i = 0; i < 5; i++)
        {
            spreadsheet.autoSizeColumn(i);
        }

        try (FileOutputStream outputStream = new FileOutputStream("Alpaca Portfolio.xlsx")) {
            workbook.write(outputStream);
        }

        System.out.println("Portfolio Metrics Written Successfully @ \"C:\\Users\\fabio\\IdeaProjects\\alpaca" +
                "portfoliometrics\\Alpaca Portfolio.xlsx\"");
    }
}
