# Self-test pattern (extracted from a shipped game root).
# Gate it behind a CLI flag and run:  godot --path game -- --verify
# Every print below is evidence: distances, health deltas, alignment dots, capture paths.
# Extend `_verify` with one numeric assertion per new feature - never claim a feature works
# without a line of output that says so.

func _verify() -> void:
    for i in 50:
        await get_tree().process_frame
    print("[verify] spawn pos=%s on_floor=%s" % [player.global_position, player.is_on_floor()])
    print("[verify] craft=%s armed=%s" % [player.craft_weapon(), player.armed])
    player.aiming = true
    for i in 40:
        await get_tree().process_frame
    await _shot("user://shot_armed.png")
    print("[verify] first_person while aiming = %s" % player.is_first_person())
    var att := _find_node_class(player, "BoneAttachment3D") as Node3D
    if att != null and att.get_child_count() > 0:
        var gun := att.get_child(0) as Node3D
        var A: Basis = att.global_transform.basis
        var want_world: Vector3 = -(player.get_node("SpringArm3D/Camera3D") as Camera3D).global_transform.basis.z
        var v_local: Vector3 = (A.inverse() * want_world).normalized()
        var have_world: Vector3 = -gun.global_transform.basis.z
        print("[verify] gun: barrel_now=%s want=%s v_local=%s aligned=%.2f"
            % [have_world, want_world, v_local, have_world.dot(want_world)])
    await _shot("user://shot_fp_aim.png")
    var drone: Area3D = null
    var best := 1e9
    for c in get_children():
        if String(c.name).begins_with("Drone"):
            var d: float = (c as Area3D).global_position.distance_to(player.global_position)
            if d < best:
                best = d
                drone = c as Area3D
    var cam: Camera3D = player.get_node("SpringArm3D/Camera3D")
    for i in 3:
        var to := drone.global_position - cam.global_position
        player.yaw = atan2(-to.x, -to.z)
        player.rotation.y = player.yaw
        player.pitch = rad_to_deg(asin(clampf(to.normalized().y, -1.0, 1.0)))
        for j in 3:
            await get_tree().process_frame
    var hp_before: int = drone.hp
    var q := PhysicsRayQueryParameters3D.create(cam.global_position,
            cam.global_position + (-cam.global_transform.basis.z) * 200.0)
    q.collide_with_areas = true
    q.collide_with_bodies = true
    q.exclude = [player.get_rid()]
    var r := get_world_3d().direct_space_state.intersect_ray(q)
    print("[verify] probe collider=%s hit_pos=%s drone_pos=%s drone_layer=%d cam_forward=%s"
          % [r.get("collider"), r.get("position"), drone.global_position, drone.collision_layer,
             -cam.global_transform.basis.z])
    player._try_fire()
    for i in 4:
        await get_tree().process_frame
    print("[verify] shot at drone dist=%.1f hp %d -> %d ammo=%d" % [best, hp_before, drone.hp, player.ammo])
    for i in 14:
        await get_tree().process_frame
    await _shot("user://shot_fp_fire.png")
    await _inspect("user://shot_weapon.png")
    player._try_fire()
    player._try_fire()
    player._try_fire()
    for i in 4:
        await get_tree().process_frame
    print("[verify] after 4 shots: drone hp=%d ammo=%d" % [drone.hp, player.ammo])
    await _shot("user://shot_fire.png")
    # mouse-look regression: inject a motion event and confirm the view turns
    # (this is the path that was gated on pointer lock and broke in the browser)
    player.rotation.y = 0.0
    player.yaw = 0.0
    player.pitch = 0.0
    var mm := InputEventMouseMotion.new()
    mm.relative = Vector2(-120.0, -80.0)
    Input.parse_input_event(mm)
    await get_tree().process_frame
    print("[verify] mouse look: yaw %.0f -> %.0f deg, pitch %.1f -> %.1f deg"
        % [0.0, rad_to_deg(player.yaw), 0.0, player.pitch])

    # curb step-up check: stand on the east-west road and walk north into the 16 cm curb
    player.global_position = Vector3(-60.0, 0.3, -5.0)
    player.rotation.y = 0.0
    player.yaw = 0.0
    player.pitch = 0.0
    for i in 10:
        await get_tree().physics_frame
    Input.action_press("move_forward")
    for i in 100:
        player.rotation.y = 0.0     # pin facing: the real mouse can rotate a captured window
        player.yaw = 0.0
        await get_tree().physics_frame
    Input.action_release("move_forward")
    var pp: Vector3 = player.global_position
    print("[verify] curb walk: x=-60 start z=-5.0 -> z=%.2f y=%.2f (step-up ok if z < -8)" % [pp.z, pp.y])
    # vehicle check: steal it, drive, get out
    if vehicles.size() > 0:
        var veh: Node3D = vehicles[0]
        var v0: Vector3 = veh.global_position
        player.enter_vehicle(veh)
        await get_tree().physics_frame
        Input.action_press("move_forward")
        for i in 150:
            await get_tree().physics_frame
        Input.action_release("move_forward")
        var names := []
        for c in veh.get_slide_collision_count():
            var col = veh.get_slide_collision(c).get_collider()
            names.append(String(col.get_parent().name) if col.get_parent() != null else String(col.name))
        print("[verify] veh dbg: on_floor=%s pos=%s colliders=%s" % [veh.is_on_floor(), veh.global_position, names])
        print("[verify] vehicle %s: drove %.1f m, speed %.1f m/s, player riding=%s"
            % [veh.kind, v0.distance_to(veh.global_position), veh.speed, player.is_driving()])
        player.exit_vehicle()
        print("[verify] exit: player=%s vehicle=%s"
            % [player.global_position.round(), veh.global_position.round()])

    # humanoid enemy: closes distance and opens fire once the player is armed
    player.armed = true
    player.hp = 100.0
    var g: Node3D = _find_named(self, "goon0")
    if g != null:
        g.global_position = player.global_position + Vector3(0, 0, -13)
        var d0: float = g.global_position.distance_to(player.global_position)
        var hp0: float = player.hp
        for i in 300:
            await get_tree().physics_frame
        print("[verify] goon: dist %.1f -> %.1f, player hp %.0f -> %.0f"
            % [d0, g.global_position.distance_to(player.global_position), hp0, player.hp])

    # quadruped mech
    player.hp = 100.0
    var m: Node3D = _find_named(self, "mech0")
    if m != null:
        m.global_position = player.global_position + Vector3(0, 0, -18)
        var md0: float = m.global_position.distance_to(player.global_position)
        var hp1: float = player.hp
        for i in 300:
            await get_tree().physics_frame
        print("[verify] mech: dist %.1f -> %.1f, player hp %.0f -> %.0f"
            % [md0, m.global_position.distance_to(player.global_position), hp1, player.hp])

    print("[verify] window size=%s" % [get_viewport().get_visible_rect().size])
    get_tree().quit()
