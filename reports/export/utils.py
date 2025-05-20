import io
import pandas as pd
from django.http import HttpResponse

def export_to_excel(dataframe, filename, scheme):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Report')

        workbook = writer.book
        worksheet = writer.sheets['Report']
        worksheet.write('A1', f"Scheme: {scheme.name}")
        worksheet.write('A2', f"Reg #: {scheme.registration_number}")
        worksheet.write('A3', f"FSP #: {scheme.fsp_number}")

    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}.xlsx'
    return response
