import datetime

import factory
import faker
import hamsterlib


class CategoryFactory(factory.Factory):
    pk = None
    name = factory.Faker('word')

    class Meta:
        model = hamsterlib.Category


class ActivityFactory(factory.Factory):
    pk = None
    name = factory.Faker('word')
    category = factory.SubFactory(CategoryFactory)
    deleted = False

    class Meta:
        model = hamsterlib.Activity


class FactFactory(factory.Factory):
    pk = None
    activity = factory.SubFactory(ActivityFactory)
    start = faker.Faker().date_time()
    end = start + datetime.timedelta(hours=3)
    description = factory.Faker('paragraph')

    class Meta:
        model = hamsterlib.Fact

0
