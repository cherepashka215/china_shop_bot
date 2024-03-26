from googleapiclient import discovery
from google_auth_httplib2 import AuthorizedHttp
from google.oauth2 import service_account
import re
import json


DISCOVERY_SERVICE_URL = "https://sheets.googleapis.com/$discovery/rest?version=v4"
SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


class GSheets:
    def __init__(self, creds_json_file: str = None, creds_account_info: str = None):
        credentials = None
        if creds_account_info:
            creds_json = json.loads(creds_account_info)
            credentials = service_account.Credentials.from_service_account_info(
                creds_json, scopes=SCOPES
            )
        elif creds_json_file:
            credentials = service_account.Credentials.from_service_account_file(
                creds_json_file, scopes=SCOPES
            )
        http = AuthorizedHttp(credentials)
        self.service = discovery.build(
            "sheets", "v4", http=http, discoveryServiceUrl=DISCOVERY_SERVICE_URL
        )

    def get_sheet_names(self, spreadsheet_url: str):
        spreadsheet_id = self._get_sheet_id_from_url(spreadsheet_url)
        sheet_metadata = (
            self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        sheets = sheet_metadata.get("sheets")

        sheet_names = []
        for sheet in sheets:
            sheet_names.append(sheet.get("properties", {}).get("title", "Лист1"))

        return sheet_names

    def get_sheet_values(self, spreadsheet_url: str, list_name: str):
        spreadsheet_id = self._get_sheet_id_from_url(spreadsheet_url)
        result = (
            self.service.spreadsheets()
                .values()
                .get(
                spreadsheetId=spreadsheet_id, range=f"{list_name}", majorDimension="ROWS"
            )
                .execute()
        )
        values_list = result.get("values")

        return values_list

    @staticmethod
    def _get_sheet_id_from_url(url: str):
        url_key_re_v2 = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")
        m = url_key_re_v2.search(url)

        return m.group(1)

    @staticmethod
    def _convert_column_number_to_letter(column_int: int):
        start_index = 1  # it can start either at 0 or at 1
        letter = ''
        while column_int > 25 + start_index:
            letter += chr(65 + int((column_int - start_index) / 26) - 1)
            column_int = column_int - (int((column_int - start_index) / 26)) * 26
        letter += chr(65 - start_index + (int(column_int)))

        return letter

    def _get_sheet_titles(self, spreadsheet_id: str, list_name: str):
        # получение заголовков столбцов в таблице
        result = (
            self.service.spreadsheets()
                .values()
                .get(
                spreadsheetId=spreadsheet_id, range=f"{list_name}!1:1", majorDimension="ROWS"
            )
                .execute()
        )
        titles_list = result.get("values")
        titles = titles_list[0] if titles_list else []

        return titles

    def get_row_by_primary_field(
            self, spreadsheet_id: str, list_name: str, primary_field_name: str, primary_field_value
    ) -> dict:
        """
        Получение значений из нужного ряда по уникальному номеру строки
        :param spreadsheet_id: id таблицы
        :param list_name: имя листа для поиска
        :param primary_field_name: наименование колонки, в которой содержится номер
        :return: список значений из найденной строки
        """
        # получили заголовки таблицы
        titles = self._get_sheet_titles(spreadsheet_id, list_name)
        # ищем номер столбца, в котором содержатся ключевые значения
        primary_col_num = titles.index(primary_field_name) + 1
        primary_col_letter = self._convert_column_number_to_letter(primary_col_num)

        # в ключевом столбце ищем нужное нам значение
        result = (
            self.service.spreadsheets()
                .values()
                .get(
                spreadsheetId=spreadsheet_id,
                range=f"{list_name}!{primary_col_letter}1:{primary_col_letter}",
                majorDimension="COLUMNS",
            )
                .execute()
        )

        res_list = result.get("values", [])

        primary_cell_list = [
            index
            for (index, item) in enumerate(res_list[0] if res_list else [])
            if item == primary_field_value
        ]
        if not primary_cell_list:
            return {}

        # получаем строку по найденному индексу
        row = (
            self.service.spreadsheets()
                .values()
                .get(
                spreadsheetId=spreadsheet_id,
                range=f"{list_name}!{primary_cell_list[0]+1}:{primary_cell_list[0]+1}",
                majorDimension="ROWS",
            )
                .execute()
        )

        res_list = row.get("values", [])

        return dict(zip(titles, res_list[0])) if res_list else {}
