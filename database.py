from pymongo import MongoClient
from datetime import datetime
from config import MONGODB_URL, PER_REFER

class Database:
    def __init__(self, mongodb_uri=MONGODB_URL):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client['telegram_bot277']
        self.users = self.db['users']
        self.stats = self.db['stats']
        self.join_requests = self.db['join_requests']
        self._init_stats()

    def _init_stats(self):
        if not self.stats.find_one({'_id': 'global_stats'}):
            self.stats.insert_one({
                '_id': 'global_stats',
                'total_users': 0,
                'total_withdrawals': 0,
                'total_withdrawal_amount': 0,
                'total_refers': 0
            })

    def create_user(self, user_id, referrer_id=None):
        if not self.users.find_one({'_id': user_id}):
            user_data = {
                '_id': user_id,
                'referred_users': 0,
                'balance': 0,
                'wallet': "none",
                'withdrawals': 0,
                'last_bonus': None,
                'referrer': referrer_id if referrer_id else user_id,
                'refer_claimed': False,
                'created_at': datetime.now()
            }
            self.users.insert_one(user_data)
            self.stats.update_one(
                {'_id': 'global_stats'},
                {'$inc': {'total_users': 1}},
                upsert=True
            )
            return True
        return False

    def add_referral(self, referrer_id, bonus_amount):
        result = self.users.update_one(
            {'_id': referrer_id},
            {
                '$inc': {
                    'referred_users': 1,
                    'balance': bonus_amount
                }
            }
        )
        if result.modified_count > 0:
            self.stats.update_one(
                {'_id': 'global_stats'},
                {'$inc': {'total_refers': 1}},
                upsert=True
            )
            return True
        return False

    def claim_referral_bonus(self, user_id, referrer_id):
        user = self.users.find_one({'_id': user_id})
        if user and not user.get('refer_claimed', False):
            self.users.update_one(
                {'_id': user_id},
                {'$set': {'refer_claimed': True}}
            )
            return self.add_referral(referrer_id, PER_REFER)
        return False

    def save_join_request(self, user_id, channel_id):
        data = {
            'user_id': str(user_id),
            'channel_id': str(channel_id),
            'created_at': datetime.now()
        }
        self.join_requests.insert_one(data)
        return True
    
    def check_join_request(self, user_id, channel_id):
        query = {
            'user_id': str(user_id),
            'channel_id': str(channel_id),
        }
        return self.join_requests.find_one(query) is not None

    def get_user(self, user_id):
        return self.users.find_one({'_id': user_id})

    def update_wallet(self, user_id, wallet_address):
        return self.users.update_one(
            {'_id': user_id},
            {'$set': {
                'wallet': wallet_address,
                'updated_at': datetime.now()
            }}
        )

    def update_balance(self, user_id, amount):
        return self.users.update_one(
            {'_id': user_id},
            {
                '$inc': {'balance': amount},
                '$set': {'updated_at': datetime.now()}
            }
        )

    def get_balance(self, user_id):
        user = self.get_user(user_id)
        return user['balance'] if user else 0

    def get_wallet(self, user_id):
        user = self.get_user(user_id)
        return user['wallet'] if user else "none"

    def process_withdrawal(self, user_id, amount):
        result = self.users.update_one(
            {
                '_id': user_id,
                'balance': {'$gte': amount}
            },
            {
                '$inc': {
                    'balance': -amount,
                    'withdrawals': 1
                },
                '$set': {'last_withdrawal': datetime.now()}
            }
        )
        if result.modified_count > 0:
            self.stats.update_one(
                {'_id': 'global_stats'},
                {
                    '$inc': {
                        'total_withdrawals': 1,
                        'total_withdrawal_amount': amount
                    }
                },
                upsert=True
            )
            return True
        return False

    def update_bonus_time(self, user_id):
        return self.users.update_one(
            {'_id': user_id},
            {'$set': {
                'last_bonus': datetime.now(),
                'updated_at': datetime.now()
            }}
        )

    def can_claim_bonus(self, user_id):
        user = self.get_user(user_id)
        if not user or not user.get('last_bonus'):
            return True
        time_diff = datetime.now() - user['last_bonus']
        return time_diff.total_seconds() >= 86400

    def get_referral_count(self, user_id):
        user = self.get_user(user_id)
        return user['referred_users'] if user else 0

    def get_stats(self):
        stats = self.stats.find_one({'_id': 'global_stats'})
        if not stats:
            self._init_stats()
            stats = self.stats.find_one({'_id': 'global_stats'})
        return stats

    def get_top_referrers(self, limit=10):
        return list(self.users.find(
            {},
            {'_id': 1, 'referred_users': 1}
        ).sort('referred_users', -1).limit(limit))

    def get_total_users(self):
        return self.users.count_documents({})

    def __del__(self):
        try:
            self.client.close()
        except:
            pass