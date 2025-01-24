from pymongo import MongoClient
from datetime import datetime
from config import MONGODB_URL, REFERRALS_PER_LEVEL
import math


class Database:
    def __init__(self, mongodb_uri=MONGODB_URL):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client['telegram_bot2096365']
        self.users = self.db['users9']
        self.stats = self.db['stats3']
        self._init_stats()

    def _init_stats(self):
        if not self.stats.find_one({'_id': 'global_stats'}):
            self.stats.insert_one({
                '_id': 'global_stats',
                'total_users': 0,
                'total_referrals': 0
            })

    def calculate_level(self, referral_count):
        if referral_count < REFERRALS_PER_LEVEL:
            return 1
        return 1 + math.floor(referral_count / REFERRALS_PER_LEVEL)

    def get_next_level_requirements(self, current_referrals):
        current_level = self.calculate_level(current_referrals)
        referrals_needed = (current_level * REFERRALS_PER_LEVEL) - current_referrals
        return referrals_needed

    def create_user(self, user_id, referrer_id=None, first_name=None, username=None):
        if not self.users.find_one({'_id': user_id}):
            user_data = {
                '_id': user_id,
                'first_name': first_name,
                'username': username,
                'referrer': referrer_id if referrer_id else None,
                'referred_users': 0,
                'level': 1,
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

    def get_user(self, user_id):
        return self.users.find_one({'_id': user_id})

    def add_referral(self, referrer_id):
        user = self.get_user(referrer_id)
        if not user:
            return False

        current_referrals = user.get('referred_users', 0)
        current_level = user.get('level', 1)

        new_referrals = current_referrals + 1
        new_level = self.calculate_level(new_referrals)

        update_data = {
            '$inc': {'referred_users': 1},
            '$set': {'level': new_level}
        }

        result = self.users.update_one(
            {'_id': referrer_id},
            update_data
        )

        if result.modified_count > 0:
            self.stats.update_one(
                {'_id': 'global_stats'},
                {'$inc': {'total_referrals': 1}},
                upsert=True
            )
            return {
                'success': True,
                'leveled_up': new_level > current_level,
                'new_level': new_level
            }
        return {'success': False}

    def claim_referral_bonus(self, user_id, referrer_id):
        user = self.get_user(user_id)
        if user and not user.get('refer_claimed', False):
            self.users.update_one(
                {'_id': user_id},
                {'$set': {'refer_claimed': True}}
            )
            return self.add_referral(referrer_id)
        return {'success': False}

    def get_user_level_info(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None

        referral_count = user.get('referred_users', 0)
        current_level = self.calculate_level(referral_count)
        next_level = current_level + 1
        referrals_needed = self.get_next_level_requirements(referral_count)

        return {
            'current_level': current_level,
            'referral_count': referral_count,
            'next_level': next_level,
            'referrals_needed': referrals_needed,
            'referrals_per_level': REFERRALS_PER_LEVEL
        }

    def get_users_with_referrals(self):
        return list(self.users.find(
            {'referred_users': {'$gt': 0}},
            {'_id': 1, 'first_name': 1, 'username': 1, 'referred_users': 1, 'level': 1}
        ).sort('referred_users', -1))

    def get_referred_users(self, user_id):
        return list(self.users.find(
            {'referrer': user_id},
            {'_id': 1, 'first_name': 1, 'username': 1}
        ))

    def get_referred_usernames(self, user_id):
        referred_users = self.get_referred_users(user_id)
        return [f"{user['username']}" if user.get('username') else user['first_name'] for user in referred_users]

    def get_total_users(self):
        return self.users.count_documents({})

    def get_stats(self):
        stats = self.stats.find_one({'_id': 'global_stats'})
        if not stats:
            self._init_stats()
            stats = self.stats.find_one({'_id': 'global_stats'})
        return stats
