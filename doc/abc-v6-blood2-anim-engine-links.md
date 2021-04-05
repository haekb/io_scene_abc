# Blood 2

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

Nodes can be extended with additional nodes by appending _extra# to the node name with a number starting from 1, eg. torso_extra1, torso_extra2

## ABCv6 Animation Names

For (multiplayer?) characters:
- idle1
- idle2
- idle3
- idle4
- talk1
- talk2
- talk3
- talk4
- talk5
- walk_nogun
- walk_rifle
- walk_pistol
- walk_knife1
- walk_irleg_rifle (injured right leg)
- walk_irleg_nogun (injured right leg)
- walk_illeg_rifle (injured left leg)
- walk_illeg_nogun (injured left leg)
- run_nogun
- run_rifle
- run_pistol
- run_knife1
- jmp_rifle
- jmp_pistol
- jmp_knife
- crouch_1pistol
- crouch_rifle
- crouch_knife1
- crawl_1pistol
- crawl_rifle
- crawl_knife1
- swim_nogun
- swim_rifle
- swim_pistol
- swim_knife1
- strafe_right_nogun
- strafe_right_1pistol
- strafe_right_2pistol
- strafe_right_rifle
- strafe_right_nogun
- strafe_right_1pistol
- strafe_right_2pistol
- strafe_right_rifle
- pickup_weapon
- switch_weapon_2pistol
- switch_weapon_rifle
- switch_weapon_knife
- switch_weapon_none
- fire_stand_rifle
- fire_stand_autorifle
- fire_stand_1pistol
- fire_stand_2pistol
- fire_stand_knife1
- fire_stand_knife2
- fire_stand_knife3
- fire_stand_grenade
- fire_stand_magic
- fire_walk_rifle
- fire_walk_autorifle
- fire_walk_1pistol
- fire_walk_2pistol
- fire_walk_knife1
- fire_walk_knife2
- fire_walk_knife3
- fire_walk_grenade
- fire_walk_magic
- fire_run_rifle
- fire_run_autorifle
- fire_run_1pistol
- fire_run_2pistol
- fire_run_knife1
- fire_run_knife2
- fire_run_knife3
- fire_run_grenade
- fire_run_magic
- fire_jump_rifle
- fire_jump_autorifle
- fire_jump_1pistol
- fire_jump_2pistol
- fire_jump_knife1
- fire_jump_knife2
- fire_jump_knife3
- fire_jump_grenade
- fire_jump_magic
- fire_crouch_rifle
- fire_crouch_autorifle
- fire_crouch_1pistol
- fire_crouch_2pistol
- fire_crouch_knife1
- fire_crouch_knife2
- fire_crouch_knife3
- fire_crouch_grenade
- fire_crouch_magic
- fire_crawl_rifle
- fire_crawl_autorifle
- fire_crawl_1pistol
- fire_crawl_2pistol
- fire_crawl_knife1
- fire_crawl_knife2
- fire_crawl_knife3
- fire_crawl_grenade
- fire_crawl_magic
- falling
- falling_uncontrol
- roll_forward
- roll_right
- roll_left
- roll_back
- handspring_forward
- handspring_right
- handspring_left
- handspring_back
- flip_forward
- flip_right
- flip_left
- flip_back
- dodge_right
- dodge_left
- recoil_head1
- recoil_chest1
- recoil_rchest1
- recoil_lchest1
- recoil_lleg1
- recoil_rleg1
- recoil_head2
- recoil_chest2
- recoil_rchest2
- recoil_lchest2
- recoil_lleg2
- recoil_rleg2
- taunt_dance1
- taunt_dance2
- taunt_dance3
- taunt_dance4
- taunt_flip
- taunt_wave
- taunt_beg
- spot_right
- spot_left
- spot_point
- death_head1
- death_chest1
- death_rchest1
- death_lchest1
- death_lleg1
- death_rleg1
- death_head2
- death_chest2
- death_rchest2
- death_lchest2
- death_lleg2
- death_rleg2
- humiliation_01
- humiliation_02
- humiliation_03
- humiliation_04
- humiliation_05
- special1
- special2
- special3
- special4
- special5
- special6
- special7
- special8
- special9
- corpse_head1
- corpse_chest
- corpse_rchest
- corpse_lchest
- corpse_lleg1
- corpse_rleg1
- corpse_head2
- corpse_chest2
- corpse_rchest2
- corpse_lchest2
- corpse_lleg2
- corpse_rleg2

For dismemberment system:
- limb_head
- limb_arm
- limb_leg

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

For weapon pickup models:
- handheld

## ABCv6 Frame String Commands

For characters/enemies:
- fire_key:optional int attack_num
- show_weapon:int weapon_num
- extra_key:string extra_args - this could be anything, depending on the class using the model, see AI_Mgr::MC_Extra
- play_sound:string sound_file
  - sound_random:int max
  - sound_radius:int radius
  - sound_volume:int volume
  - sound_chance:int chance [0-100]
  - sound_voice:bool is_voice

For PV weapons:
- fire_key
- sound_key:string sound_file
- soundloop_key:string sound_file
- soundstop_key
- hide_key:string node_name
- show_key:string node_name

## Examples:

- For a gun's PV animation to deal damage the actual fire frame needs: fire_key
- To play mon_footstep_1.wav or mon_footstep_2.wav randomly whenever a footstep frame happens: [play_sound:mon_footstep_][sound_random:2][sound_volume:50]