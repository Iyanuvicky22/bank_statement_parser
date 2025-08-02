from bank_parser.model import *
from bank_parser.utils.utils import *
from bank_parser.wrangler import *


def etl():

    ab = pdf_extractor()

    ac = clean_df(ab)

    ad = shift_and_rejoin_df(ac)

    ae = clean_balance_col(ad)

    af = categorize_transactions(ae, bank='Opay')

    trans_df = transform_df(af)

    load_data(trans_df)


if __name__ == '__main__':
    etl()