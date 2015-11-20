"""
Admin interface is a Command Line interface for Administrators that want to view user and system information
"""

import termcolor
import argparse

import sys, os
sys.path.append(os.path.abspath(".."))

from dkmonitor.utilities.db_interface import DbViewer
from dkmonitor.config.config_reader import ConfigReader

from dkmonitor.utilities.new_db_int import DataBase, DirectoryStats, UserStats
from dkmonitor.config.settings_manager import export_settings

class DataBaseViewer(DataBase):

    def __init__(self,
                 db_type='postgresql',
                 hostname='127.0.0.1',
                 database='postgres',
                 username='postgres',
                 password=''):
        super().__init__(db_type=db_type,
                         hostname=hostname,
                         database=database,
                         username=username,
                         password=password)

    def get_all_users(self): ##
        session = self.create_session()
        return [username for username in session.query(UserStats.username).distinct()]

    def get_users_on_system(self, hostname):
        session = self.create_session()
        return [username for username in session.query(UserStats.username).filter(UserStats.hostname==hostname).distinct()]

    def get_users_on_system_disk(self, hostname, diskname):
        session = self.create_session()
        return [username for username in session.query(UserStats.username).filter(UserStats.hostname==hostname).filter(UserStats.target_path==diskname).distinct()]

    def get_user_stats(self, username):
        pass

    def get_all_systems(self): ##
        session = self.create_session()
        return [hostname for hostname in session.query(DirectoryStats.hostname).distinct()]

    def get_all_disks_on_system(self, hostname):
        session = self.create_session()
        return [disk for disk in session.query(DirectoryStats.target_path).filter(DirectoryStats.hostname==hostname).distinct()]

    def get_all_disks_on_all_systems(self):
        session = self.create_session()
        return [disk for disk in session.query(DirectoryStats.target_path).distinct()]

    def get_agregate_system_stats(self):
        disks = self.get_all_disks_on_all_systems()



class AdminStatViewer(DataBase):
    def __init__(self,
                 db_type='postgresql',
                 hostname='127.0.0.1',
                 database='postgres',
                 username='postgres',
                 password=''):
        super().__init__(db_type=db_type,
                         hostname=hostname,
                         database=database,
                         username=username,
                         password=password)

    def print_color_key(self):
        """Print the color key"""

        print("Color Key----------")
        green = termcolor.colored("green", "green")
        print("{} == Decrease".format(green))
        yellow = termcolor.colored("yellow", "yellow")
        print("{} == No Change".format(yellow))
        red = termcolor.colored("red", "red")
        print("{} == Increase".format(red))
        print("-------------------")


    def display_user(self, user_name):
        """
        Displays user stats in color with information gathered by the
        DbViewer object from the dkmonitor database
        """

        self.print_color_key()
        user_stats = self.get_user_stats(user_name)
        if user_stats != {}:
            print("User Name: {}".format(user_stats["user_name"]))
            for system, disks in user_stats["systems"].items():
                print("|System Name: {}".format(system))
                for disk, d_stats in disks.items():
                    print("||Disk Name: {}".format(disk))
                    if d_stats[6] > 1:
                        colored_size = termcolor.colored(str(round(d_stats[4]/1024/1024/1024, 2)), "red")
                    elif d_stats[6] == 1:
                        colored_size = termcolor.colored(str(round(d_stats[4]/1024/1024/1024, 2)), "yellow")
                    else:
                        colored_size = termcolor.colored(str(round(d_stats[4]/1024/1024/1024, 2)), "green")
                    print("|||Total File Size    : {} GB".format(colored_size))
                    if d_stats[8] > 1:
                        colored_access = termcolor.colored(str(round(d_stats[7], 2)), "red")
                    elif d_stats[8] == 1:
                        colored_size = termcolor.colored(str(round(d_stats[7]/1024/1024/1024, 2)), "yellow")
                    else:
                        colored_access = termcolor.colored(str(round(d_stats[7], 2)), "green")
                    print("|||Average File Age: {} days".format(colored_access))
                print("")

        else:
            print("User Not found")

    def display_lastest(self, hostname):
        session = self.create_session()
        obj = session.query(DirectoryStats).order_by(DirectoryStats.datetime.desc()).limit(2).all()
        for row in obj:
            for column in row.__table__.columns:
                print(column.name)
                print(getattr(row, column.name))

    def display_system(self, hostname):
        """
        Displays system stats in color with information gathered by the
        DbViewer object from the dkmonitor database
        """

        #session = self.create_session()
        #for disk in session.query(DirectoryStats).filter(DirectoryStats.hostname==hostname).distinct().all()]

        self.print_color_key()
        system_stats = self.get_system_stats(system_host_name)
        if system_stats != {}:
            print("System Name: {}".format(hostname))
            for disk, d_stats in system_stats["disks"].items():
                print("|Disk Name: {}".format(disk))
                if d_stats['disk_stats'][5] > 1:
                    colored_size = termcolor.colored(str(round(d_stats['disk_stats'][3]/1024/1024/1024, 2)), "red")
                elif d_stats['disk_stats'][5] > 1:
                    colored_size = termcolor.colored(str(round(d_stats['disk_stats'][3]/1024/1024/1024, 2)), "yellow")
                else:
                    colored_size = termcolor.colored(str(round(d_stats['disk_stats'][3]/1024/1024/1024, 2)), "green")
                print("||Total File Size    : {} GB".format(colored_size))

                if d_stats['disk_stats'][7] > 1:
                    colored_access = termcolor.colored(str(round(d_stats['disk_stats'][6], 2)), "red")
                elif d_stats['disk_stats'][7] == 1:
                    colored_access = termcolor.colored(str(round(d_stats['disk_stats'][6], 2)), "yellow")
                else:
                    colored_access = termcolor.colored(str(round(d_stats['disk_stats'][6], 2)), "green")
                print("||Average File Age: {} days".format(colored_access))

                print("|Users on: {}".format(disk))
                for user in d_stats["users"]:
                    print("|| {}".format(user))
        else:
            print("System Not Found")

    def display_users(self):
        """Displays all users"""
        session = self.create_session()
        for username in session.query(UserStats.username).distinct():
            print(username)

    def display_systems(self):
        """Displays all systems"""
        session = self.create_session()
        for hostname in session.query(DirectoryStats.hostname).distinct():
            print(hostname)


def get_args(args):
    """Gets args from argparse"""

    description = """
    Administrator Interface is a program That allows you to view system and user
    data stored in a central database managed by the appilcation dkmonitor
    """
    parser = argparse.ArgumentParser(description=description)

    subparser = parser.add_subparsers()
    system_parser = subparser.add_parser("system")
    system_parser.set_defaults(which="system")
    system_parser.add_argument("system_host_name", help="Name of system or user you want to search for")

    user_parser = subparser.add_parser("user")
    user_parser.set_defaults(which="user")
    user_parser.add_argument("user_name", help="Name of system or user you want to search for")

    all_parser = subparser.add_parser("all")
    all_parser.set_defaults(which="all")
    all_parser.add_argument("display_name", help="Name of system or user you want to search for")

    return parser.parse_args(args)


def main(args=None):
    """Main function that runs the command line interface"""

    if args is None:
        args = sys.argv[1:]

    admin_int = AdminInterface()
    args = get_args(args)

    if args.which == "system":
        admin_int.display_system(args.system_host_name)
    elif args.which == "user":
        admin_int.display_user(args.user_name)
    elif args.which == "all":
        if args.display_name == "users":
            admin_int.display_users()
        elif args.display_name == "systems":
            admin_int.display_systems()
        else:
            print("ERROR: display_name must be either 'users' or 'system'")



if __name__ == "__main__":
    settings = export_settings()
    adminviewer = AdminStatViewer(**settings["DataBase_Settings"])
    adminviewer.display_lastest("circe.rc.pdx.edu")
    #main()

