#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import gettext
import traceback
import sys
import time
import json
from ikabot.config import *
from ikabot.helpers.botComm import *
from ikabot.helpers.gui import enter, enter
from ikabot.helpers.varios import wait, getDateTime
from ikabot.helpers.signals import setInfoSignal
from ikabot.helpers.pedirInfo import getIslandsIds
from ikabot.helpers.getJson import getIsland
from ikabot.helpers.process import set_child_mode

t = gettext.translation(
    "searchForIslandSpaces", localedir, languages=languages, fallback=True
)
_ = t.gettext


def searchForIslandSpaces(session, event, stdin_fd, predetermined_input):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    event : multiprocessing.Event
    stdin_fd: int
    predetermined_input : multiprocessing.managers.SyncManager.list
    """
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    try:
        if checkTelegramData(session) is False:
            event.set()
            return
        banner()
        print(
            "Do you want to search for spaces on your islands or a specific set of islands?"
        )
        print("(0) Exit")
        print("(1) Search all islands I have colonised")
        print("(2) Search a specific set of islands")
        choice = read(min=0, max=2)
        islandList = []
        if choice == 0:
            event.set()
            return
        elif choice == 2:
            banner()
            print(
                "Insert the coordinates of each island you want searched like so: X1:Y1, X2:Y2, X3:Y3..."
            )
            coords_string = read()
            coords_string = coords_string.replace(" ", "")
            coords = coords_string.split(",")
            for coord in coords:
                coord = "&xcoord=" + coord
                coord = coord.replace(":", "&ycoord=")
                html = session.get("view=island" + coord)
                island = getIsland(html)
                islandList.append(island["id"])
        else:
            pass

        banner()
        print(
            "How frequently should the islands be searched in minutes (minimum is 3)?"
        )
        time = read(min=0, digit=True)
        banner()
        print(
            "Do you wish to be notified when a fight breaks out and stops on a city on these islands? (Y|N)"
        )
        fights = read(values=["y", "Y", "n", "N"])
        banner()
        print(_("I will search for changes in the selected islands"))
        enter()
    except KeyboardInterrupt:
        event.set()
        return

    set_child_mode(session)
    event.set()

    info = _("\nI search for new spaces each hour\n")
    setInfoSignal(session, info)
    try:
        do_it(session, islandList, time, fights)
    except Exception as e:
        sendToBot(session, "Error in searchForIslandSpaces")
    finally:
        session.logout()


def do_it(session, islandList, time, fights):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
        Session object
    islandList : list[dict]
        A list containing island objects which should be searched, if an empty list is passed, all the user's colonised islands are searched
    time : int
        The time in minutes between two consecutive seraches
    fights : str
        String that can either be y or n. Indicates whether or not to scan for fight activity on islands
    """

    # this dict will contain all the cities from each island
    # as they where in last scan
    cities_before_per_island = {}

    while True:
        # this is done inside the loop because the user may colonize in a new island
        if islandList != []:
            islandsIds = islandList
        else:
            islandsIds = getIslandsIds(session)
        for islandId in islandsIds:
            html = session.get(island_url + islandId)
            island = getIsland(html)
            # cities in the current island
            cities_now = [
                city_space
                for city_space in island["cities"]
                # if city_space["type"] != "empty"
            ]  # loads the islands non empty cities into ciudades

            # if we haven't scaned this island before,
            # save it and do nothing
            if islandId not in cities_before_per_island:
                cities_before_per_island[islandId] = cities_now.copy()
            else:
                cities_before = cities_before_per_island[islandId]

                # someone disappeared
                cityPosition = 0
                for city_before in cities_before:

                    if city_before["id"] not in [
                        city_now["id"] for city_now in cities_now
                    ]:

                        # params = {
                        #     "view": "colonize",
                        #     "islandId": islandId,
                        #     "position": cityPosition,
                        #     "destinationIslandId": islandId,
                        #     "backgroundView": "island",
                        #     "currentIslandId": islandId,
                        #     "templateView": "colonize",
                        #     "actionRequest": actionRequest,
                        #     "ajax": "1",
                        # }

                        # response = session.post(params=params)

                        params2 = {
                            "action": "transportOperations",
                            "function": "startColonization",
                            "islandId": islandId,
                            "cargo_people": "40",
                            "cargo_gold": "9000",
                            "desiredPosition": cityPosition,
                            "actionRequest": actionRequest,
                            "cargo_resource": "0",
                            "cargo_tradegood1": "0",
                            "cargo_tradegood2": "0",
                            "cargo_tradegood3": "0",
                            "cargo_tradegood4": "0",
                            "capacity": "5",
                            "max_capacity": "5",
                            "jetPropulsion": "0",
                            "transporters": "3",
                            "position": cityPosition,
                            "destinationIslandId": islandId,
                            "backgroundView": "island",
                            "currentIslandId": islandId,
                            "templateView": "colonize",
                            "ajax": "1",
                        }

                        response2 = session.post(params=params2)
                        json.loads(response2, strict=False)
                        sendToBot(session, "Congrats Cought a spot in island")

                    cityPosition = cityPosition + 1
                    if fights.lower() == "y":
                        for city_now in cities_now:
                            if city_now["id"] == city_before["id"]:
                                if (
                                    "infos" in city_now
                                    and "infos" not in city_before
                                    and "armyAction" in city_now["infos"]
                                    and city_now["infos"]["armyAction"] == "fight"
                                ):
                                    sendToBot(session, "A Fight started")
                                if (
                                    "infos" not in city_now
                                    and "infos" in city_before
                                    and "armyAction" in city_before["infos"]
                                    and city_before["infos"]["armyAction"] == "fight"
                                ):

                                    sendToBot(session, "A fight stopped")

                # someone colonised
                for city_now in cities_now:
                    if city_now["id"] not in [
                        city_before["id"] for city_before in cities_before
                    ]:
                        # we didn't find the city_now in the cities_before

                        sendToBot(session, "A new City created in island")

                cities_before_per_island[islandId] = (
                    cities_now.copy()
                )  # update cities_before_per_island for the current island
        session.setStatus(
            f'Checked islands {str([int(i) for i in islandsIds]).replace(" ","")} @ {getDateTime()[-8:]}'
        )
        print("check")
        wait(time)
