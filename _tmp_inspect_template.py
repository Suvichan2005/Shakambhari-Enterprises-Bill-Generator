import os
from config import TEMPLATE_EXCEL_FILE
import openpyxl
print('TEMPLATE:', TEMPLATE_EXCEL_FILE)
wb=openpyxl.load_workbook(TEMPLATE_EXCEL_FILE, data_only=False)
ws=wb.active
for r in range(28, 41):
    vals=[ws[f'{c}{r}'].value for c in ['A','B','C','D','E','F','G','H','I']]
    print(r, vals)
wb.close()
