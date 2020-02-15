from passlib.handlers.pbkdf2 import pbkdf2_sha256
from peewee import ValuesList
from playhouse.migrate import PostgresqlMigrator, migrate

from api.models import database, PushCampaign, CustomizationSetting, Recipient

migrator = PostgresqlMigrator(database)


@database.atomic()
def migrate_1():
    migrate(
        migrator.rename_column(
            PushCampaign._meta.table_name,
            'password',
            PushCampaign.password_hash.column_name),
        migrator.rename_column(
            CustomizationSetting._meta.table_name,
            'email_text',
            CustomizationSetting.email_body_text.column_name),
        migrator.rename_column(
            Recipient._meta.table_name,
            'target',
            Recipient.target_shop.column_name))


@database.atomic()
def migrate_2():
    with_pass = PushCampaign \
        .select() \
        .where(PushCampaign.password_hash.is_null(False))
    if not with_pass:
        return
    to_update = ValuesList([
        (c.id, pbkdf2_sha256.hash(c.password_hash))
        for c in with_pass], columns=['id', 'password_hash'], alias='passhash')
    PushCampaign \
        .update({'password_hash': to_update.c.password_hash}) \
        .from_(to_update) \
        .where(PushCampaign.id == to_update.c.id) \
        .execute()


if __name__ == '__main__':
    migrate_1()
    database.evolve(ignore_tables=['basemodel', 'passwordprotectedmodel'])
    migrate_2()
