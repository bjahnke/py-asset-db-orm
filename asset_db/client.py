
from sqlalchemy.orm import Session
from asset_db.model import Stock # Your ORM models

# class DatabaseClient:
#     def __init__(self, session: Session):
#         self.session = session

#     def push_price_history(self, data: pd.DataFrame, stock_id: int):
#         """
#         Pushes price history data to the `stock_data` and `timestamp_data` tables.

#         :param data: A pandas DataFrame containing price history. Must include:
#                      'timestamp', 'open', 'close', 'high', 'low', 'volume'.
#         :param stock_id: The ID of the stock associated with the data.
#         :raises: ValueError if required columns are missing or transaction fails.
#         """
#         required_columns = {'timestamp', 'open', 'close', 'high', 'low', 'volume'}
#         if not required_columns.issubset(data.columns):
#             raise ValueError(f"DataFrame must include columns: {required_columns}")

#         try:
#             # Prepare data for `timestamp_data`
#             timestamp_rows = [
#                 TimestampDatum(
#                     interval="1d",  # Example, adjust as needed
#                     timestamp=row['timestamp'],
#                     data_source="api_example"  # Example, adjust as needed
#                 )
#                 for _, row in data.iterrows()
#             ]
#             self.session.add_all(timestamp_rows)
#             self.session.flush()  # Get primary keys for timestamp_data

#             # Prepare data for `stock_data`
#             stock_data_rows = [
#                 StockDatum(
#                     bar_number=index + 1,  # Example bar_number, adjust as needed
#                     stock_id=stock_id,
#                     close=row['close'],
#                     open=row['open'],
#                     high=row['high'],
#                     low=row['low'],
#                     volume=row['volume'],
#                     bar_number=timestamp_row.bar_number  # Map timestamp PK
#                 )
#                 for index, (timestamp_row, (_, row)) in enumerate(zip(timestamp_rows, data.iterrows()))
#             ]
#             self.session.add_all(stock_data_rows)

#             # Commit transaction
#             self.session.commit()
#         except Exception as e:
#             self.session.rollback()
#             raise ValueError(f"Failed to push price history: {e}")


def delete_table(session, table):
    session.execute(f"DELETE FROM {table}")
    session.commit()

def add_stock_data(stock: Stock, data, session):
    # Reformat the data to fit db model
    stock = stock.get_or_create(session)

    data = data.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
    data = data.reset_index().rename(columns={'Date': 'timestamp'})
    data['interval'] = stock.interval
    data['data_source'] = stock.data_source
    data['stock_id'] = stock.id
    data.to_sql('stock_data', session.bind, if_exists='append', index=False)

    return stock.id


from asset_db.model import Stock
from sqlalchemy import text

class MyStock(Stock):
    @classmethod
    def get_by_id(cls, session, stock_id) -> Stock:
        return session.query(cls).filter(cls.id == stock_id).first()
    
    def get_or_create(self, session) -> Stock:
        """returns data from the db if it exists, otherwise creates it"""
        stock = session.query(Stock).filter(
            Stock.symbol == self.symbol and
            Stock.is_relative == self.is_relative and
            Stock.interval == self.interval and
            Stock.data_source == self.data_source and
            Stock.market_index == self.market_index and
            Stock.sec_type == self.sec_type
        ).first()
        if stock:
            return stock
        session.add(self)
        session.commit()
        return self
    
    def add_stock_data(self, data, session):
        # Reformat the data to fit db model
        stock = self.get_or_create(session)

        # data = data.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        # data = data.reset_index().rename(columns={'Date': 'timestamp'})
        # data['interval'] = stock.interval
        # data['data_source'] = stock.data_source
        data['stock_id'] = stock.id

        json_data = data.to_json(orient='records')

        session.execute(
            text("CALL insert_unique_timestamp_data(:data)"),
            {'data': json_data}
        )
        session.commit()
        return stock.id