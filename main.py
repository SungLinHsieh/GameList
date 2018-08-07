import os.path
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from time import sleep
from datetime import datetime
import pandas as pd

def GetOrderNumberList(driver):
    have_seen_all = None
    OrderNumbers = []

    while not have_seen_all:
        try:
            have_seen_all = driver.find_element_by_class_name('ordersContainer__listEnd')
        except NoSuchElementException:
            driver.find_element_by_xpath('//body').send_keys(Keys.END)
            sleep(3)

    for Order in driver.find_elements_by_class_name('orderHeader__number'):
        if Order.text not in OrderNumbers:
            OrderNumbers.append(Order.text)
    return OrderNumbers

def Login(driver):
    driver.get('https://www.bestbuy.com/profile/ss/orderlist')
    email_cell= driver.find_element_by_xpath('//*[@id="fld-e"]')
    email_cell.send_keys("")
    passwd_cell = driver.find_element_by_xpath('//*[@id="fld-p1"]')
    passwd_cell.send_keys("")
    passwd_cell.send_keys(Keys.RETURN)

    wait = WebDriverWait(driver, 15)
    wait.until(EC.title_contains('Best Buy Purchases'))

def ReadOrderNumbers(PathToFile):
    OrderNumbers = []
    with open(PathToFile, 'r') as f:
        for line in f.readlines():
            if line != '':
                OrderNumbers.append(line.strip())
    return OrderNumbers

def WriteOrderNumbers(PathToFile, OrderNumbers):
    with open(PathToFile, 'w') as f:
        for OrderNumber in OrderNumbers:
            if OrderNumber != '':
                f.write(OrderNumber + '\n')

def CheckCompleteItem(OrderNumber, driver):
    OrderDetailUrl = 'https://www.bestbuy.com/profile/ss/orders/order-details?orderId='
    driver.get(OrderDetailUrl + OrderNumber)
    Complete = True
    for item in driver.find_elements_by_class_name('item-status__text'):
        Complete = \
            Complete and (item.text == 'Delivered' or item.text == 'Canceled' )
    return Complete

def CheckCompleteItems(PathToData, OrderNumbers, driver):
    CompletedOrders = ReadOrderNumbers(PathToData + 'CompletedOrders.txt')
    RevCompletedOrders = CompletedOrders.copy()
    CostumCompletedOrders = ReadOrderNumbers(PathToData + \
                                             'CostumCompletedOrders.txt')
   
    OrderNumbers = GetOrderNumberList(driver)
    for OrderNumber in OrderNumbers:
        if OrderNumber in CompletedOrders or \
           OrderNumber in CostumCompletedOrders:
            print('skip '+OrderNumber)
            continue
        elif CheckComplete(OrderNumber, driver):
            print('found new completed order:' + OrderNumber)
            RevCompletedOrders.append(OrderNumber)

    if RevCompletedOrders != CompletedOrders:
        print('Write file')
        WriteOrderNumbers(PathToData + 'CompletedOrders.txt', \
                          RevCompletedOrders)

def GetOrderDate(driver):
    sleep(1)
    Month = driver.find_element_by_class_name('date-block__month').text
    Day = driver.find_element_by_class_name('date-block__day').text
    Year = driver.find_element_by_class_name('date-block__year').text
    OrderDate =  datetime.strptime(Month + Day +Year,'%b%d%Y')
    return OrderDate

def GetReleaseDateSKU(driver, url):
    driver.get(url)
    wait = WebDriverWait(driver,10)
    wait.until(lambda driver: driver.find_element_by_class_name('footer-wrap'))
    try:
        driver.find_element_by_class_name('c-alert-icon')
        ReleaseDate = '-'
        SKU = '-'
    except NoSuchElementException:
        ReleaseDateText = driver.find_element_by_class_name('release-date')\
            .text.split(':')[1].replace(' ','')
        if ReleaseDateText == 'NotYetAnnounced':
            ReleaseDate = '-'
        else:
            ReleaseDate = datetime.strptime(ReleaseDateText, '%m/%d/%Y')
        SKU = driver.find_element_by_class_name('sku-id').\
            text.split(':')[1].replace(' ','')
    return (ReleaseDate, SKU)

def Console2str(Console):
    if Console == 'Switch':
        ScannedOrdersFileName = 'ScannedOrders-Switch.txt'
        CSVFileName = 'SwitchGames.csv'
        KeyWord = 'Nintendo Switch'
    elif Console == 'PS4':
        ScannedOrdersFileName = 'ScannedOrders-PS4.txt'
        CSVFileName = 'PS4Games.csv'
        KeyWord = 'PlayStation 4'
    elif Console == '3DS':
        ScannedOrdersFileName = 'ScannedOrders-3DS.txt'
        CSVFileName = '3DSGames.csv'
        KeyWord = 'Nintendo 3DS'
    return (ScannedOrdersFileName, CSVFileName, KeyWord)

def GetMatchedItems(driver, KeyWord):
    sleep(1)
    ItemStatusList = [elemet.text for elemet in \
                    driver.find_elements_by_class_name('item-status__text')]
    ItemNameList = [elemet.text for elemet in \
                    driver.find_elements_by_class_name('item-name')]
    print(ItemNameList)
    RegularItemIdx = []
    for idx, ItemStatus in enumerate(ItemStatusList):
        if ItemStatus != 'Canceled':
            RegularItemIdx.append(idx)
    MatchedItems = []
    for idx in RegularItemIdx:
        if KeyWord in ItemNameList[idx] and \
           not('Digital' in ItemNameList[idx]):
            MatchedItems.append(idx)
            print('Matched item: ' + ItemNameList[idx])
        else:
            print('Unmatched item: ' + ItemNameList[idx])
    return MatchedItems

def GetClassText(driver, ClassName):
    return [element.text for element in \
                     driver.find_elements_by_class_name(ClassName)]

def ConsoleGames(Console, PathToData, PathToReport, OrderNumbers, driver):
    ColumnNames = ['Name', 'OrderDate', 'ReleaseDate', 'EffectiveDate', \
                   'Status' ,'Price', 'SKU']
    (ScannedOrdersFileName, CSVFileName, KeyWord) = Console2str(Console)
    
    if os.path.isfile(PathToData + ScannedOrdersFileName):
        ScannedOrders = ReadOrderNumbers(PathToData + ScannedOrdersFileName)
    else:
        ScannedOrders = []
    RevScannedOrders = ScannedOrders.copy()

    if os.path.isfile(PathToReport + CSVFileName):
        Report = pd.read_csv(PathToReport + CSVFileName)
    else:
        Report = pd.DataFrame(columns = ColumnNames )

    for OrderNumber in OrderNumbers:
        if OrderNumber in ScannedOrders:
            continue
        OrderDetailUrl = 'https://www.bestbuy.com/profile/ss/orders/order-details?orderId='
        driver.get(OrderDetailUrl + OrderNumber)
        print("Doing " + OrderNumber)
        MatchedItems = GetMatchedItems(driver, KeyWord)
        # create new df
        df = pd.DataFrame(columns = ColumnNames)

        names = GetClassText(driver, 'item-name')
        prices = GetClassText(driver, 'item-total__header-block')
        statuses = GetClassText(driver, 'item-status__text')
        AddressNames = GetClassText(driver, 'address__name')[1:]
        MatchedItemsLink = \
            [driver.find_element_by_link_text(ItemName).get_attribute("href") \
             for ItemName in [names[idx] for idx in MatchedItems]]
        OrderDate = GetOrderDate(driver)
        for i, idx in enumerate(MatchedItems):
            df.loc[i] = None
            if AddressNames[idx] != "Sung-Lin Hsieh":
                continue
            #print('adding ' + names[idx].split(' - ')[0])
            df.Name[i] = names[idx].split(' - ')[0]
            df.OrderDate[i] = OrderDate.strftime("%Y-%m-%d")
            (ReleaseDate, SKU) = GetReleaseDateSKU(driver, MatchedItemsLink[i])  
            if ReleaseDate == '-':
                df.ReleaseDate[i] = '-'
                df.EffectiveDate[i] = '-'
            else:
                df.ReleaseDate[i] = ReleaseDate.strftime("%Y-%m-%d")
                df.EffectiveDate[i] = max(OrderDate, ReleaseDate).strftime("%Y-%m-%d")
            df.SKU[i] = SKU
            df.Price[i] = prices[idx].split('\n')[1]
            df.Status[i] = statuses[idx]
        Report = Report.append(df, ignore_index = True)        
        RevScannedOrders.append(OrderNumber)
    Report = Report.sort_values(by='EffectiveDate', ascending = False)
    if RevScannedOrders != ScannedOrders:
        WriteOrderNumbers(PathToData + ScannedOrdersFileName, RevScannedOrders)
    Report.to_csv(PathToReport + CSVFileName, index = False)

    return Report
        
def main():
    PathToData = "./Data/"
    PathToReport = './Report/'
    if not os.path.exists(PathToData):
        os.makedirs(PathToData)
    option = webdriver.ChromeOptions()
    #option.add_argument('headless')
    driver = webdriver.Chrome(chrome_options=option)
    Login(driver)
    OrderNumbers = GetOrderNumberList(driver)
    #CheckCompleteItems(PathToData, OrderNumbers, driver)
    ConsoleGames('Switch', PathToData, PathToReport, OrderNumbers, driver)
    #ConsoleGames('PS4', PathToData, PathToReport, OrderNumbers, driver)
    #ConsoleGames('3DS', PathToData, PathToReport, OrderNumbers, driver)
    
    #browser.close()

if __name__ == '__main__':
    main()
