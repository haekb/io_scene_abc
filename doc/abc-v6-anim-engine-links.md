## ABCv6 Node Names

For dismemberment/locational damage system:

- head
- neck
- torso
- pelvis
- ru_arm
- rl_arm
- r_hand
- lu_arm
- ll_arm
- l_hand
- lu_leg
- ll_leg
- l_ankle
- l_foot
- ru_leg
- rl_leg
- r_ankle
- r_foot
- obj
- l_gun
- r_gun

## ABCv6 Animation Names

Animation names for PV weapon models:

- static_model
- idle
- draw
- dh_draw
- holster
- dh_holster
- start_fire
- fire
- end_fire
- start_alt_fire
- alt_fire
- end_alt_fire

## ABCv6 Frame String Commands

- fire_key:optional int attack_num
- show_weapon:int weapon_num
- extra_key:unknown
- play_sound:string sound_file
	sound_random:int max
	sound_radius:int radius
	sound_volume:int volume
	sound_chance:int chance [0-100]
	sound_voice:bool is_voice

# Examples:

- For a gun's PV animation to deal damage the actual fire frame needs: fire_key
- To play mon_footstep_1.wav or mon_footstep_2.wav randomly whenever a footstep frame happens: [play_sound:mon_footstep_][sound_random:2][sound_volume:50]