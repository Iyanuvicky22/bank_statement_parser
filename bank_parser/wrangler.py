import pandas as pd
import pymupdf
import numpy as np
from bank_parser.utils.utils import check_datetime
from bank_parser.utils.logger import logger


FILEPATH = r"opay_bs\opay_bankstatement.pdf"


def pdf_extractor() -> pd.DataFrame:

    tables = []
    try:
        with pymupdf.open(FILEPATH) as doc:
            for page_number in range(len(doc)):
                page = doc.load_page(page_number)
                text_blocks = page.get_text("blocks")

                sorted_blocks = sorted(text_blocks, key=lambda b: b[1])

                table_data = []
                for block in sorted_blocks:
                    lines = block[4].split("\n")
                    table_data.append(lines)

                if table_data:
                    df = pd.DataFrame(table_data)
                    processed_df = df

                    if not processed_df.empty:
                        tables.append(processed_df)

            if tables:
                concatenated_df = pd.concat(tables, ignore_index=True)
                bank_statement = concatenated_df
            else:
                bank_statement = pd.DataFrame()
        return bank_statement
    except Exception as e:
        logger.error(
            "Error in pdf_extractor function: ", e
            )


def clean_df(data: pd.DataFrame) -> pd.DataFrame:
    try:
        # Renaming Columns
        col = [
            "Trans.Time",
            "Value Date",
            "Description",
            "Debit/Credit(#)",
            "Balance(#)",
            "Channel",
            "Transaction Reference",
            "NoneDrop",
        ]
        data.columns = col

        # Dropping multiple headers and rows with irrelevant values.
        bs_df = data.copy()
        bs_df = bs_df.drop(bs_df[bs_df["Trans.Time"] == "Trans. Time"].index)
        bs_df = bs_df[~bs_df["Trans.Time"].str.contains("^[A-Z]", regex=True)]

        # Ensure Datetime consistency
        bs_df = bs_df[bs_df.apply(check_datetime, axis=1)]

        return bs_df
    except Exception as e:
        logger.error("Error in clean_df function: ", e)


def shift_and_rejoin_df(data: pd.DataFrame) -> pd.DataFrame:
    try:
        # Split dataset into two.
        nas_dropped = data.dropna(subset=["Balance(#)"]).reset_index()
        df_to_shift = nas_dropped[~(nas_dropped["Channel"] == "E-Channel")].reset_index()
        df_stable = nas_dropped[nas_dropped["Channel"] == "E-Channel"].reset_index()

        # Selecting Transformation Criteria
        shift_criteria = (
            df_to_shift["Trans.Time"]
            .str.contains('r"\b\d{2} [A-Za-z]{3} \d{4}\b"', regex=True)
            .notna()
        )

        for index in shift_criteria.index:
            index = int(index)
            df_to_shift.iloc[index, :] = df_to_shift.iloc[index, :].shift()
        df_shifted = df_to_shift

        final_df = pd.concat([df_stable, df_shifted], axis=0)
        final_df = final_df.drop(
            columns=["level_0", "index", "Trans.Time", "NoneDrop"]
        ).reset_index()
        final_df = final_df.drop(columns="index")
        return final_df
    except Exception as e:
        logger.error("Error in shift and rejoin function: ", e)


def clean_balance_col(data: pd.DataFrame) -> pd.DataFrame:
    try:
        data["Debit/Credit(#)"] = pd.to_numeric(
            data["Debit/Credit(#)"].str.replace(",", "").str.replace("+", ""),
            errors="coerce",
        )
        data["Balance(#)"] = pd.to_numeric(
            data["Balance(#)"].str.replace(",", ""), errors="coerce"
        )
        calculated_balance = data["Balance(#)"].copy()

        # Iterate row-by-row and calculate missing balances
        for i in range(1, len(calculated_balance)):
            if pd.isna(calculated_balance[i]):
                if not pd.isna(calculated_balance[i - 1]) and not pd.isna(
                    data.loc[i, "Debit/Credit(#)"]
                ):
                    calculated_balance[i] = round(calculated_balance[i - 1], 2) + round(
                        data.loc[i, "Debit/Credit(#)"], 2
                    )
        data["Balance(#)"] = calculated_balance

        data['Credit'] = round(data['Debit/Credit(#)'].apply(lambda x:x if x > 0 else 0), 2)
        data['Debit'] = abs(round(data['Debit/Credit(#)'].apply(lambda x:x if x < 0 else 0), 2))
        data = data.drop(columns='Debit/Credit(#)')
        return data
    except Exception as e:
        logger.error("Error in clean_balance_col function: ", e)


def categorize_transactions(data: pd.DataFrame, bank: str) -> pd.DataFrame:
    try:
        data["Description"] = data["Description"].apply(
            lambda x: x.replace("Transfer from ", "").replace("Transfer to ", "")
        )

        conditions = [
            (
                (data["Description"].isin(["OWealth Deposit(AutoSave)", "OWealth Deposit"]))
                & (data["Credit"] > 0)
            ),
            (
                (data["Description"].isin(["OWealth Deposit(AutoSave)", "OWealth Deposit"]))
                & (data["Debit"] > 0)
            ),
            ((data["Description"] == "OWealth Withdrawal") & (data["Credit"] > 0)),
        ]

        choices = ["OWealth Deposit", "OWealth Withdrawal", "OWealth Deposit"]

        data["Description"] = np.select(conditions, choices, default=data["Description"])
        data['Bank'] = bank
        data['Trans_count'] = range(1, len(data['Description'])+1)
        return data
    except Exception as e:
        logger.error("Error from categorize_transactions logic: ", e)


def transform_df(data: pd.DataFrame)-> pd.DataFrame:
    try:
        def transform_row(row):
            return {
                "trans_no": row["Trans_count"],
                "type": "debit" if int(row["Debit"]) > 0 else "credit",
                "amount": row["Debit"] if int(row["Debit"]) > 0 else row["Credit"],
                "narration": row["Description"].replace(r"'", ""),
                "date": row["Value Date"],
                "balance": row["Balance(#)"],
                "bank": row["Bank"]
            }
        transformed_bs = data.apply(transform_row, axis=1).tolist()
        transformed_bs_df = pd.DataFrame(transformed_bs)
        return transformed_bs_df
    except Exception as e:
        logger.error("Error in data transformation: ", e)
