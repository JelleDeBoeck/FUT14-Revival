import asyncio

from server.blaze.protocol import (
    build_association_lists_body,
    build_clubs_component_settings_body,
    build_clubs_invitations_body,
    build_fetch_config_body,
    build_fire_notification,
    build_fire_response,
    build_fut_entitlements_body,
    build_messaging_fetch_body,
    build_origin_login_body,
    build_osdk_setting_groups_body,
    build_osdk_settings_body,
    build_ping_body,
    build_post_auth_body,
    build_pre_auth_body,
    build_stats_groups_body,
    build_stats_key_scopes_body,
    build_stats_period_ids_body,
    build_user_added_body,
    build_user_authenticated_body,
    build_user_extended_data_body,
    extract_tdf_string,
    extract_tdf_string_list,
    parse_fire_header,
    tdf_string,
)


HOST = "127.0.0.1"
PORT = 42128


async def send_response(
    writer,
    *,
    component,
    command,
    sequence,
    body=b"",
    name="response",
):
    response = build_fire_response(
        component=component,
        command=command,
        sequence=sequence,
        body=body,
    )

    writer.write(response)
    await writer.drain()

    print(
        f"[BLAZE] {name} sent "
        f"({len(response)} bytes)"
    )


async def send_notification(
    writer,
    *,
    component,
    command,
    body,
    name,
):
    packet = build_fire_notification(
        component,
        command,
        body,
    )

    writer.write(packet)
    await writer.drain()

    print(
        f"[BLAZE] notification {name} sent "
        f"({len(packet)} bytes)"
    )


async def send_login_notifications(writer):
    # Give FIFA a moment to register its
    # UserSessions listeners.
    await asyncio.sleep(0.25)

    await send_notification(
        writer,
        component=0x7802,
        command=8,
        body=build_user_authenticated_body(),
        name="UserAuthenticated",
    )

    await asyncio.sleep(0.05)

    await send_notification(
        writer,
        component=0x7802,
        command=2,
        body=build_user_added_body(),
        name="UserAdded",
    )

    await asyncio.sleep(0.05)

    await send_notification(
        writer,
        component=0x7802,
        command=1,
        body=build_user_extended_data_body(),
        name="UserExtendedData",
    )


async def handle_client(reader, writer):
    peer = writer.get_extra_info("peername")

    print(f"[BLAZE] connection from {peer}")

    try:
        while True:
            header = await reader.readexactly(12)

            (
                length,
                component,
                command,
                error,
                type_options,
                options_raw,
                sequence,
            ) = parse_fire_header(header)

            if length:
                body = await reader.readexactly(length)
            else:
                body = b""

            print(
                "[BLAZE] request "
                f"component={component} "
                f"command={command} "
                f"sequence={sequence} "
                f"length={length}"
            )

            # Don't dump the OriginLogin token.
            if component == 1 and command == 0x98:
                print("[BLAZE] OriginLogin payload redacted")

            elif body:
                print(body.hex(" "))

            # -----------------------------------------
            # Util.PreAuth
            # -----------------------------------------
            if component == 9 and command == 7:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_pre_auth_body(),
                    name="PreAuth response",
                )

            # -----------------------------------------
            # Util.Ping
            # -----------------------------------------
            elif component == 9 and command == 2:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_ping_body(),
                    name="Ping response",
                )

            # -----------------------------------------
            # Util.FetchClientConfig
            # -----------------------------------------
            elif component == 9 and command == 1:
                config_id = extract_tdf_string(
                    body,
                    b"CFID",
                )

                print(
                    "[BLAZE] FetchClientConfig:",
                    config_id,
                )

                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_fetch_config_body(config_id),
                    name=f"Config response ({config_id})",
                )

            # -----------------------------------------
            # Util.PostAuth
            # -----------------------------------------
            elif component == 9 and command == 8:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_post_auth_body(),
                    name="PostAuth response",
                )

            # -----------------------------------------
            # Authentication.OriginLogin
            # -----------------------------------------
            elif component == 1 and command == 0x98:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_origin_login_body(),
                    name="OriginLogin response",
                )

                await send_login_notifications(writer)

            # -----------------------------------------
            # Authentication entitlements
            # 0x1D = 29
            # 0x20 = 32
            # -----------------------------------------
            elif (
                component == 1
                and command in (0x1D, 0x20)
            ):
                requested_groups = extract_tdf_string_list(
                    body,
                    b"GNLS",
                )

                print(
                    "[BLAZE] requested entitlement groups:",
                    requested_groups,
                )

                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_fut_entitlements_body(
                        requested_groups=requested_groups,
                    ),
                    name="FUT Entitlements response",
                )

            # -----------------------------------------
            # Authentication.Logout
            # -----------------------------------------
            elif component == 1 and command == 0x46:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=b"",
                    name="Logout response",
                )

            # -----------------------------------------
            # Messaging.FetchMessages
            # component 15 command 2
            # -----------------------------------------
            elif component == 15 and command == 2:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_messaging_fetch_body(),
                    name="Messaging Fetch response",
                )

            # -----------------------------------------
            # Association Lists
            # component 25 command 6
            # -----------------------------------------
            elif component == 25 and command == 6:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_association_lists_body(),
                    name="Association Lists response",
                )

            # -----------------------------------------
            # Clubs component settings
            # component 11 command 2600
            # -----------------------------------------
            elif component == 11 and command == 2600:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_clubs_component_settings_body(),
                    name="Clubs Settings response",
                )

            # -----------------------------------------
            # Clubs invitations
            # component 11 command 1600
            # -----------------------------------------
            elif component == 11 and command == 1600:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_clubs_invitations_body(),
                    name="Clubs Invitations response",
                )

            # -----------------------------------------
            # Stats key scopes
            # component 7 command 15
            # -----------------------------------------
            elif component == 7 and command == 15:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_stats_key_scopes_body(),
                    name="Stats KeyScopes response",
                )

            # -----------------------------------------
            # Stats groups
            # component 7 command 3
            # -----------------------------------------
            elif component == 7 and command == 3:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_stats_groups_body(),
                    name="Stats Groups response",
                )

            # -----------------------------------------
            # Stats period IDs
            # component 7 command 20
            # -----------------------------------------
            elif component == 7 and command == 20:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_stats_period_ids_body(),
                    name="Stats PeriodIds response",
                )

            # -----------------------------------------
            # OSDK settings
            # component 2249 command 1
            # -----------------------------------------
            elif component == 2249 and command == 1:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_osdk_settings_body(),
                    name="OSDK Settings response",
                )

            # -----------------------------------------
            # OSDK setting groups
            # component 2249 command 2
            # -----------------------------------------
            elif component == 2249 and command == 2:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=build_osdk_setting_groups_body(),
                    name="OSDK Setting Groups response",
                )

            # -----------------------------------------
            # UserSessions update acknowledgement
            # component 0x7802 command 20
            # -----------------------------------------
            elif component == 0x7802 and command == 20:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=b"",
                    name="UserSessions Update ACK",
                )

            # -----------------------------------------
            # Census subscribe
            # component 10 command 1
            # -----------------------------------------
            elif component == 10 and command == 1:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=b"",
                    name="Census Subscribe response",
                )

            # -----------------------------------------
            # Rooms update subscription
            # component 21 command 10
            # -----------------------------------------
            elif component == 21 and command == 10:
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=b"",
                    name="Rooms Update response",
                )

            # -----------------------------------------
            # Sponsored Events
            # component 0x081C command 3
            # -----------------------------------------
            elif (
                component == 0x081C
                and command == 3
            ):
                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=tdf_string(
                        b"URL",
                        "http://127.0.0.1:8080/"
                        "sponsored-events",
                    ),
                    name="SponsoredEvents URL response",
                )

            # -----------------------------------------
            # Everything not implemented yet
            # -----------------------------------------
            else:
                print(
                    "[BLAZE] unknown request "
                    f"component={component} "
                    f"command={command}"
                )

                await send_response(
                    writer,
                    component=component,
                    command=command,
                    sequence=sequence,
                    body=b"",
                    name="Empty response",
                )

    except asyncio.IncompleteReadError:
        pass

    except ConnectionResetError:
        pass

    except Exception as exc:
        print(f"[BLAZE] error: {exc!r}")

    finally:
        print(f"[BLAZE] disconnected: {peer}")

        writer.close()

        try:
            await writer.wait_closed()
        except (ConnectionResetError, OSError):
            pass


async def main():
    server = await asyncio.start_server(
        handle_client,
        HOST,
        PORT,
    )

    print(f"[BLAZE] listening on {HOST}:{PORT}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())