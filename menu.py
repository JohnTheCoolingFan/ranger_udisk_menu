#!/usr/bin/python3
# coding: utf-8
# License: The MIT License
# Author: Alexander Lutsai <sl_ru@live.com>
# Year: 2021
# Description: This script draws menu to choose, mount and unmount drives

import curses
import curses.ascii
import json
import subprocess


class ChoosePartition:
    blkinfo: str = None
    screen = None
    selected_partn = 1
    partn = 1
    help_message = [("Press 'm' to mount, " +
                     "'u' to unmount, " +
                     "'g' to refresh"),
                    "  and 'e' to unmount the whole drive"]
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
            partn += len(bd['children'])

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

    def _select_print_part(self, part, is_selected, i):
        if not ('mountpoint' in part and
                'name' in part and
                'size' in part):
            raise Exception('Wrong lsblk json format. No mountpoint, name or size in the partition')
        label = ""
        label_fields = ['label', 'partlabel', 'parttypename', 'fstype']
        for f in label_fields:
            if f not in part:
                continue
            if part[f] is not None:
                label = part[f]
                break

        mp = "Not mounted"
        if part['mountpoint'] is not None:
            mp = part['mountpoint']

        s = "{name:<12} {size:<8} {label:<16} {mp}".format(
            name=part['name'] if part['name'] is not None else "None",
            label=label if label is not None else "None",
            size=part['size'] if part['size'] is not None else "None",
            mp=mp
        )
        self.screen.addstr(2 + i, 4, s, curses.color_pair(is_selected))

    def _select_print_block_device(self, bd, i):
        if not ('model' in bd and
                'size' in bd or
                'name' in bd):
            raise Exception('Wrong lsblk json format. No model, size or name in blockdevice')

        model = bd['model'] if bd['model'] is not None else ""
        size = bd['size'] if bd['size'] is not None else ""
        self.screen.addstr(2 + i, 2, bd['name'] + " " + model + " " + size)

    # Unused variable is for future uses maybe?
    def _select_print(self, x):
        self.screen.clear()
        self.screen.border(0)
        self.screen.addstr(1, 2, self.help_message[0])
        self.screen.addstr(2, 2, self.help_message[1])

        partn = 0
        i = 0
        if 'blockdevices' not in self.blkinfo:
            raise Exception('Wrong lsblk json format. No field "blockdevices"')
        for bd in self.blkinfo['blockdevices']:
            i += 1
            bd_selected = False
            bd_i = i
            self._select_print_block_device(bd, bd_i)
            if 'children' not in bd:
                continue
            for part in bd['children']:
                i += 1
                partn += 1
                is_selected = 0 if self.selected_partn != partn else 1
                if is_selected:
                    bd_selected = True
                self._select_print_part(part, is_selected, i)
            if bd_selected:
                self.screen.addstr(2 + bd_i, 1, ">")
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
        key = 0
        # quit when pressed `q` or `Esc` or `Ctrl+g`
        while key not in (ord('q'), curses.ascii.ESC, curses.ascii.BEL):
            self._select_print(key)
            key = self.screen.getch()
            if key in (ord('j'), curses.ascii.SO, curses.KEY_DOWN):
                # down
                self.selected_partn += 1
                if self.selected_partn > self.partn:
                    self.selected_partn = self.partn
            elif key in (ord('k'), curses.ascii.DLE, curses.KEY_UP):
                # up
                self.selected_partn -= 1
                if self.selected_partn <= 0:
                    self.selected_partn = 1
            elif key == ord('e'):
                self._eject_all()
            elif key == ord('m'):
                sel = self._get_part_by_partn()
                if sel is not None:
                    self.mount(sel['path'])
            elif key == ord('u'):
                sel = self._get_part_by_partn()
                if sel is not None:
                    self.unmount(sel['path'])
            elif key == ord('g') or key == ord('r'):
                self._read_partitions()
        curses.endwin()

    def _udisk_mount_unmount(self, cmd, dev):
        r = ""
        try:
            r = subprocess.run(['udisksctl', cmd, '-b', dev],
                               capture_output=True,
                               check=True)
            r = (r.stdout.decode(encoding="utf-8") +
                 r.stderr.decode(encoding="utf-8"))
            self.message = r
        except subprocess.CalledProcessError as e:
            self.message = cmd + " error: " + r + str(e)
        self._read_partitions()

    def unmount(self, dev):
        self._udisk_mount_unmount("unmount", dev)

    def mount(self, dev):
        self._udisk_mount_unmount("mount", dev)


if __name__ == "__main__":
    cp = ChoosePartition()
    cp.select()
