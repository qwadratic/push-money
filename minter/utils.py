from mintersdk import MinterConvertor


def to_pip(bip):
    return MinterConvertor.convert_value(bip, 'pip')


def to_bip(pip):
    return MinterConvertor.convert_value(pip, 'bip')
