"""
This script Is the main managing script for the dk_monitor script suite.
This script is indented to be run as a cron job to monitor actions on any
given disk or directory that is set by the adminstrator
"""

import time
import threading

import sys
import os
sys.path.append(os.getcwd() + "/..")

from . import db_interface
#import dkmonitor.db_interface as db_interface
import dkmonitor.dk_stat as dk_stat
import dkmonitor.dk_emailer as dk_emailer
import dkmonitor.dk_clean as dk_clean
import dkmonitor.configurator_settings_obj as configurator_settings_obj
import dkmonitor.log_setup as log_setup

class MonitorManager():
    """This class is the main managing class for all other classes
    It runs preset tasks that are found in the json settings file"""

    def __init__(self):
        self.set_interface = configurator_settings_obj.SettingsInterface()
        self.settings = self.set_interface.parse_and_check_all()

        self.logger = log_setup.setup_logger("../log/monitor_log.log")

        #Configures Email api
        self.emailer = dk_emailer.Emailer(self.settings["Email_API"]["user_postfix"])

        #Configures database
        self.database = db_interface.DataBase(self.settings["DataBase_info"]["database"],
                                              self.settings["DataBase_info"]["user_name"],
                                              self.settings["DataBase_info"]["password"],
                                              self.settings["DataBase_info"]["host"])

        if self.settings["DataBase_info"]["purge_database"] == "yes":
            self.logger.info("Cleaning Database")
            self.database.clean_data_base(self.settings["DataBase_info"]["purge_after_day_number"])


    def run_task(self, task_name):
        """Runs a single task from the settings json file loaded"""

        task = self.settings["Scheduled_Tasks"][task_name]
        self.check_clean_task(task)
        #Instanciates the disk statistics object
        dk_stat_obj = dk_stat.DkStat(task["system_name"], task["directory_path"])
        print("Searching {path}".format(path=task["directory_path"]))
        self.logger.info("Searching %s", task["directory_path"])
        start = time.time()
        dk_stat_obj.dir_search() #Searches the Directory
        end = time.time()
        total = end - start
        print('----')
        print("Total time: {t}".format(t=total))
        print('----')
        print("Done. Exporting data To database...")
        self.logger.info("Exporting %s data to database", task["directory_path"])
        dk_stat_obj.export_data(self.database) #Exports data from dk_stat_obj to the database
        print("Emailing Users")
        self.logger.info("Emailing Users for %s", task["directory_path"])
        #Emails users with bad data
        if dk_stat_obj.get_disk_use_percent() > task["disk_use_percent_threshold"]:
            dk_stat_obj.email_users(self.emailer, #Emails users
                                    self.settings["Email_API"]["user_postfix"],
                                    task["last_access_threshold"],
                                    task["days_between_runs"],
                                    task["file_relocation_path"],
                                    task["bad_flag_percent"])
        print("Done")
        self.logger.info("%s scan task complete", task["directory_path"])


    def start(self):
        """starts all tasks"""

        if self.settings["Thread_Settings"]["thread_mode"] == 'yes':
            self.run_tasks_threading()
        else:
            self.run_tasks()

    def run_tasks(self):
        """Runs all tasks in the json settings file"""

        for task in self.settings["Scheduled_Tasks"].keys():
            self.run_task(task)

    def run_tasks_threading(self):
        """Runs all tasks in the json settings file with multiple threads"""

        for task in self.settings["Scheduled_Tasks"].keys():
            thread = threading.Thread(target=self.run_task, args=(task,))
            thread.daemon = False
            thread.start()

    def check_clean_task(self, task):
        """
        Checks if directory needs to be cleaned
        Starts cleaning routine if flagged
        """

        if task["relocate_old_files"] == "yes":
            query_str = self.build_query_str(task)
            collumn_names = "disk_use_percent"

            query_data = self.database.query_date_compare("directory_stats",
                                                          query_str,
                                                          collumn_names)
            if query_data == None:
                pass
            elif query_data[0] > task["disk_use_percent_threshold"]:
                self.clean_disk(task["directory_path"],
                                task["file_relocation_path"],
                                task["last_access_threshold"])

    def clean_disk(self, directory, relocation_path, access_threshold):
        """Cleaning routine function"""

        print("CLeaning...")
        self.logger.info("Cleaning %s", directory)
        thread_settings = self.settings["Thread_Settings"]
        clean_obj = dk_clean.DkClean(directory, relocation_path, access_threshold)
        if thread_settings["thread_mode"] == "yes":
            clean_obj.move_all_threaded(thread_settings["thread_number"])
        else:
            clean_obj.move_all()


    #TODO Refactor these functions
    def build_query_str(self, task):
        """Builds query string used to determine if disk needs to be cleaned"""

        query_str = "searched_directory = '{sdir}' AND system = '{sys}'"
        query_str = query_str.format(dkp=task["disk_use_percent_threshold"],
                                     sdir=task["directory_path"],
                                     sys=task["system_name"])
        return query_str



if __name__ == "__main__":
    monitor = MonitorManager()
    monitor.start()
