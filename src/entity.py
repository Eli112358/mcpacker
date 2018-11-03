entity_types = {
    'animals': [
        'cow',
        'donkey',
        'horse',
        'llama',
        'mule',
        'mushroom_cow',
        'ocelot',
        'pig',
        'polar_bear',
        'rabbit',
        'sheep',
        'wolf'
    ],
    'birds': [
        'bat',
        'chicken',
        'parrot'
    ],
    'aquatic': [
        'cod',
        'dolphin',
        'guardian',
        'pufferfish',
        'salmon',
        'squid',
        'tropical_fish',
        'turtle'
    ],
    'hostile': [
        'blaze',
        'cave_spider',
        'creeper',
        'elder_guardian',
        'enderman',
        'endermite',
        'evoker',
        'ghast',
        'guardian',
        'magma_cube',
        'phantom',
        'shulker',
        'silverfish',
        'slime',
        'spider',
        'vex',
        'vindicator',
        'witch',
    ],
    'undead': [
        'drowned',
        'husk',
        'skeleton',
        'stray',
        'wither_skeleton',
        'zombie_pigman',
        'zombie_villager',
        'zombie'
    ]
}

def is_animal(type):
    return type in entity_types['animals']
def is_aquatic(type):
    return type in entity_types['aquatic']
def is_bird(type):
    return type in entity_types['birds']
def is_hostile(type):
    return type in entity_types['hostile']
def is_undead(type):
    return type in entity_types['undead']
