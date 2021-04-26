#!/usr/bin/python3
# coding: utf-8
# License: The MIT License
# Author: Alexander Lutsai <sl_ru@live.com>
# Year: 2021
# Description: This script draws menu to choose, mount and unmount drives

import curses
import curses.ascii
import subprocess
import json


class ChoosePartition:
    blkinfo = None
    screen = None
    selected_partn = 1
    partn = 1

    message = ""

    def __init__(self):
        self.screen = curses.initscr()
        curses.start_color()
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(True)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self.selected_partn = 1
        self._read_partitions()

    def _read_partitions(self):
        r = subprocess.check_output(['lsblk', '--all', '--json', '-O'])
        self.blkinfo = json.loads(r)
        partn = 0
        for bd in self.blkinfo['blockdevices']:
            if 'children' not in bd:
                continue
            for part in bd['children']:
                partn += 1

        self.partn = partn
        if self.selected_partn > self.partn:
            self.selected_partn = self.partn
        if self.selected_partn <= 0:
            self.selected_partn = 1

    def _get_part_by_partn(self):
        partn = 0
        for bd in self.blkinfo['blockdevices']:
            if 'children' not in bd:
                continue
            for part in bd['children']:
                partn += 1
                if self.selected_partn == partn:
                    return part
        return None

    def _select_print(self, x):
        self.screen.clear()
        self.screen.border(0)
        self.screen.addstr(
            2, 2,
            "Press 'm' to mount and 'u' to unmount and 'e' to unmount the whole drive")

        partn = 0
        i = 0
        if 'blockdevices' not in self.blkinfo:
            raise Exception('Wrong lsblk json format. No field "blockdevices"')
        for bd in self.blkinfo['blockdevices']:
            i += 1
            if 'model' not in bd or 'size' not in bd or 'name' not in bd:
                raise Exception(
                    'Wrong lsblk json format. No model, size or name in the blockdevice')
            model = bd['model'] if bd['model'] is not None else ""
            size = bd['size'] if bd['size'] is not None else ""
            self.screen.addstr(2 + i, 2, bd['name'] + " " + model + " " + size)
            if 'children' not in bd:
                continue
            for part in bd['children']:
                i += 1
                partn += 1
                is_selected = 0 if self.selected_partn != partn else 1
                lab = ""
                if 'label' not in part and part['label'] is not None:
                    lab = part['label']
                elif 'partlabel' not in part and part['partlabel'] is not None:
                    lab = part['partlabel']
                elif 'parttypename' not in part and part['parttypename'] is not None:
                    lab = part['parttypename']
                elif 'fstype' not in part and part['fstype'] is not None:
                    lab = part['fstype']

                if 'mountpoint' not in part:
                    raise Exception('Wrong lsblk json format. No mountpoint')
                mp = part['mountpoint'] if part['mountpoint'] is not None else "Not mounted"

                s = "{name:<12} {size:<8} {label:<16} {mp}".format(
                    name=part['name'] if part['name'] is not None else "None",
                    label=lab if lab is not None else "None",
                    size=part['size'] if part['size'] is not None else "None",
                    mp=mp
                )
                self.screen.addstr(2 + i, 4, s, curses.color_pair(is_selected))
                self.screen.refresh()

        self.screen.addstr(2 + i + 2, 4, self.message)

    def _eject_all(self):
        blk = None
        partn = 0
        for bd in self.blkinfo['blockdevices']:
            if 'children' not in bd:
                continue
            for part in bd['children']:
                partn += 1
                if self.selected_partn == partn:
                    blk = bd
        if blk is None:
            return
        for part in blk['children']:
            self.unmount(part['path'])

    def select(self):
        sel = None
        x = 0
        # quit when pressed `q` or `Esc` or `Ctrl+g`
        while x not in (ord('q'), curses.ascii.ESC, curses.ascii.BEL):
            self._select_print(x)
            x = self.screen.getch()
            if x in (ord('j'), curses.ascii.SO, curses.KEY_DOWN):
                # down
                self.selected_partn += 1
                if self.selected_partn > self.partn:
                    self.selected_partn = self.partn
            elif x in (ord('k'), curses.ascii.DLE, curses.KEY_UP):
                # up
                self.selected_partn -= 1
                if self.selected_partn <= 0:
                    self.selected_partn = 1
            elif x == ord('e'):
                sel = self._eject_all()
            elif x == ord('m'):
                sel = self._get_part_by_partn()
                if sel is not None:
                    self.mount(sel['path'])
            elif x == ord('u'):
                sel = self._get_part_by_partn()
                if sel is not None:
                    self.unmount(sel['path'])
            elif x == ord('g') or x == ord('r'):
                self._read_partitions()
        curses.endwin()

    def _udisk_mount_unmount(self, cmd, dev):
        r = ""
        try:
            r = subprocess.run(
                ['udisksctl', cmd, '-b', dev], capture_output=True)
            r = (r.stdout.decode(encoding="utf-8") +
                 r.stderr.decode(encoding="utf-8"))
            self.message = r
        except Exception as e:
            self.message = cmd + " error: " + r + str(e)
        self._read_partitions()

    def unmount(self, dev):
        self._udisk_mount_unmount("unmount", dev)

    def mount(self, dev):
        self._udisk_mount_unmount("mount", dev)


if __name__ == "__main__":
    cp = ChoosePartition()
    cp.select()
