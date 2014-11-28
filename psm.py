#!/usr/bin/env python
import traceback
import pygtk
pygtk.require("2.0")
import gtk,gobject
import subprocess
import re
import datetime
import pickle
import pynotify
import os
pynotify.init("psm")
notification_daemon=None
try:
	n = pynotify.Notification("PSM","PSM started")
	n.show()
except:
	try:
		notification_daemon=subprocess.Popen(["/usr/lib/notification-daemon/notification-daemon"])
	except:
		print("notifications not available")

from psm_config import *

col_id=0
col_time=1
col_name=2
col_state=3
col_color=4
col_parameters=5

class JobDefinition:
	def __init__(self,name,commands,parameters,gparams):
		self.infodict={"jobname":name}
		self.infodict.update(gparams)
		self.commands=commands
		self.parameters=parameters
		self.gparameters=gparams
	
	def job_scripts(self):
		goptions=[]
		for key,val in self.infodict.iteritems():
			if key=="jobname":
				continue
			goptions.append(option_template.format(key,val))
		scripts=[]
		if len(self.parameters)==1 and self.parameters[0][0].startswith("RUN="):
			p=subprocess.Popen(self.parameters[0][0][4:].split(" "),stdout=subprocess.PIPE)
			out,err=p.communicate()
			tmp_params2=out.split("\n")
			tmp_params=[]
			for p in tmp_params2:
				if p!="":
					tmp_params.append(p.split(","))
			print("***** PARAMETERS USED *****")
			print(tmp_params)
			print("***** END *****")
		else:
			tmp_params=self.parameters
		for number in range(len(tmp_params)):
			commands=self.commands.format(*(tmp_params[number]))
			info=self.infodict.copy()
			info["outputfolder"]=OUTPUT_PATTERN.format("%j")
			info["commands"]=commands
			info["GLOBALPARAMS"]="\n".join(goptions)
			scripts.append((template.format(**info),",".join(tmp_params[number])))
		return scripts


class JobDescriptionDialog(gtk.Dialog):
	def __init__(self,parent,old_data=None):
		gtk.Dialog.__init__(self,"Job Description",parent,gtk.DIALOG_MODAL,None)
		box=self.get_content_area()

		self.jobname=gtk.Entry()
		#self.jobname.set_placeholder_text("Name")


		self.commands=gtk.TextView()
		self.commands.set_editable(True)
		self.commandbuffer=self.commands.get_buffer()
		#box.add(self.commands)

		"""self.numcpu=gtk.Entry()
		#self.numcpu.set_placeholder_text("Number of CPUs to use")
		#self.numcpu.set_input_purpose(gtk.InputPurpose.DIGITS)
		box.add(self.numcpu)"""

		#self.mempercpu=gtk.Entry()
		#self.mempercpu.set_placeholder_text("Memory per CPU (MB)")
		#self.mempercpu.set_input_purpose(gtk.InputPurpose.DIGITS)
		#box.add(self.mempercpu)

		self.params=gtk.TextView()
		self.params.set_editable(True)
		self.parambuffer=self.params.get_buffer()
		#box.add(self.params)

		self.gparams=gtk.TextView()
		self.gparams.set_editable(True)
		self.gparambuffer=self.gparams.get_buffer()
		#box.add(self.gparams)

		self.table=gtk.Table(1,4,False)
		self.table.attach(self.jobname ,0,1,0,1)
		self.table.attach(self.commands,0,1,1,2)
		self.table.attach(self.params  ,0,1,2,3)
		self.table.attach(self.gparams ,0,1,3,4)
		self.table.set_row_spacings(5)
		box.add(self.table)


		self.add_button("Cancel",gtk.RESPONSE_CANCEL)
		self.add_button("OK",gtk.RESPONSE_OK).connect("clicked",self.ok_clicked)
		self.show_all()
		self.definition=None

		if old_data is not None:
			#self.mempercpu.set_text(old_data.infodict["mempercpu"])
			info=old_data.infodict.copy()
			info.pop("jobname")
			self.jobname.set_text(old_data.infodict["jobname"])
			self.commandbuffer.set_text(old_data.commands)

			paramstrings=[]
			for p in old_data.parameters:
				paramstrings.append(",".join(p))
			self.parambuffer.set_text("\n".join(paramstrings))

			gparamstrings=[]
			for a,b in old_data.gparameters.iteritems():
				gparamstrings.append("{}={}".format(a,b))
			self.gparambuffer.set_text("\n".join(gparamstrings))

	def ok_clicked(self,widget):
		try:
			"""numcpu=self.numcpu.get_text()"""
			#mempercpu=self.mempercpu.get_text()
			jobname=self.jobname.get_text()

			commands=self.commandbuffer.get_text(self.commandbuffer.get_start_iter(),self.commandbuffer.get_end_iter())
			text=self.parambuffer.get_text(self.parambuffer.get_start_iter(),self.parambuffer.get_end_iter())
			gtext=self.gparambuffer.get_text(self.gparambuffer.get_start_iter(),self.gparambuffer.get_end_iter())

			strings=text.split("\n")
			params=[]
			for i in range(len(strings)):
				params.append(strings[i].split(","))

			gstrings=gtext.split("\n")
			gparams={}
			for i in range(len(gstrings)):
				if len(gstrings[i])==0:
					continue
				#print(gstrings[i])
				s=gstrings[i].split("=")
				a=s[0]
				b=s[1]
				gparams[a]=b

			self.definition=JobDefinition(jobname,commands,params,gparams)
		except Exception as e:
			traceback.print_exc()
			#print("***** {} *****".format(e))


class MainWindow(gtk.Window):
	#def delete_event(self,widget,data=None):
	#	return False # really quit

	def destroy(self,widget,data=None):
		self.save_job_definitions()
		self.save_jobs()
		gtk.main_quit()
	
	def add_job_to_list(self,jobid,time,name,parameters):
		self.store.append([jobid,str(time),name,"???","#000000",parameters])
	
	def notification(self,title,text):
		n = pynotify.Notification(title,text)
		try:
			n.show()
		except:
			pass
	def __init__(self):
		gtk.Window.__init__(self,gtk.WINDOW_TOPLEVEL)
		self.connect("delete_event", self.destroy)

		# JOB LIST DATA
		self.store=gtk.ListStore(int,str,str,str,str,str)
		"""self.store.append([1,"01:00:00","test.py","running","#000000"])
		self.store.append([2,"01:01:00","test.py","pending","#A0A0A0"])
		self.store.append([3,"01:02:00","test.py","done","#00A000"])
		self.store.append([4,"01:03:00","test.py","cancelled","#A0A000"])
		self.store.append([5,"01:01:00","test.py","error","#A00000"])"""

		# JOB LIST VIEW
		self.tree=gtk.TreeView(self.store)
		self.tree.append_column(gtk.TreeViewColumn("time",gtk.CellRendererText(),text=1))
		self.tree.append_column(gtk.TreeViewColumn("name",gtk.CellRendererText(),text=2))
		self.tree.append_column(gtk.TreeViewColumn("status",gtk.CellRendererText(),text=3,foreground=4))
		self.tree.append_column(gtk.TreeViewColumn("parameters",gtk.CellRendererText(),text=5))
	
		treeselection=self.tree.get_selection()
		treeselection.connect("changed",self.job_selected)
		#treeselection.set_mode(gtk.SELECTION_MULTIPLE)

		self.load_jobs()

		# JOB DEFINITION DATA
		self.definition_store=gtk.ListStore(str)
		self.definition_tree=gtk.TreeView(self.definition_store)
		self.definition_tree.append_column(gtk.TreeViewColumn("name",gtk.CellRendererText(),text=0))

		# BUTTONS
		"""self.btn_run=gtk.Button("Run selected")
		self.btn_run.connect("clicked",self.run_definition)

		self.btn_add_definition=gtk.Button("Add...")
		self.btn_add_definition.connect("clicked",self.add_definition_dialog)"""

		# JOB ACTIONS
		# STOCKS: REFRESH, add, apply, cancel, clear, close, delete, edit, new, execute
		# buttons
		job_toolbar = gtk.Toolbar()
		btn_job_refresh=gtk.ToggleToolButton(gtk.STOCK_REFRESH)
		btn_job_refresh.set_active(True)
		self.refresh_enabled=btn_job_refresh.get_active
		self.refresh_output_enabled=btn_job_refresh.get_active
		btn_job_delete=gtk.ToolButton(gtk.STOCK_DELETE)
		btn_job_clear=gtk.ToolButton(gtk.STOCK_CLEAR)
		btn_job_cancel=gtk.ToolButton(gtk.STOCK_MEDIA_STOP)

		# add buttons to toolbar
		job_toolbar.insert(btn_job_refresh,0)
		job_toolbar.insert(btn_job_delete,1)
		job_toolbar.insert(btn_job_clear,2)
		job_toolbar.insert(btn_job_cancel,3)

		# callbacks
		# btn_job_refresh needs no callback!
		btn_job_clear.connect("clicked",self.joblist_clear)
		btn_job_delete.connect("clicked",self.joblist_delete)
		btn_job_cancel.connect("clicked",self.joblist_cancel)

		# JOB DEFINITION ACTIONS
		def_toolbar = gtk.Toolbar()
		# buttons
		btn_def_execute=gtk.ToolButton(gtk.STOCK_EXECUTE)
		btn_def_new=gtk.ToolButton(gtk.STOCK_NEW)
		btn_def_edit=gtk.ToolButton(gtk.STOCK_EDIT)
		btn_def_delete=gtk.ToolButton(gtk.STOCK_DELETE)

		# add buttons to toolbar
		def_toolbar.insert(btn_def_execute,		0)
		def_toolbar.insert(gtk.SeparatorToolItem(),	1)
		def_toolbar.insert(btn_def_new,			2)
		def_toolbar.insert(btn_def_edit,		3)
		def_toolbar.insert(btn_def_delete,		4)

		# callbacks
		btn_def_execute.connect("clicked",self.run_definition)
		btn_def_new.connect("clicked",self.add_definition_dialog)
		btn_def_edit.connect("clicked",self.edit_definition_dialog)
		btn_def_delete.connect("clicked",self.delete_definition)

		# OUTPUT FILED
		self.output=gtk.TextView()
		self.output.set_editable(False)
		self.outputbuffer=self.output.get_buffer()

		# TABLE
		self.table=gtk.Table(3,2,False)
		treescroll=gtk.ScrolledWindow()
		treescroll.add(self.tree)
		self.table.attach(treescroll,0,1,1,2,yoptions=gtk.EXPAND|gtk.FILL|gtk.SHRINK,xoptions=gtk.EXPAND|gtk.FILL|gtk.SHRINK)
		self.table.attach(job_toolbar,0,1,0,1,yoptions=0)

		self.table.attach(self.definition_tree,1,2,1,2,xoptions=gtk.SHRINK)
		self.table.attach(def_toolbar,1,2,0,1,yoptions=0,xoptions=gtk.FILL)

		outputscroll=gtk.ScrolledWindow()
		outputscroll.add(self.output)
		self.table.attach(outputscroll,2,3,1,2,xoptions=gtk.FILL|gtk.EXPAND)

		self.table.set_col_spacings(5)

		# WINDOW STUFF
		self.add(self.table)
		self.show_all()

		# REGULAR UPDATES
		gobject.timeout_add_seconds(3,self.update_job_list)
		self.update_job_list(show_notifications=False)

		# LOAD DATA
		self.load_job_definitions()
	
	def joblist_clear(self,widget):
		treeiter = self.store.get_iter_first()
		while treeiter != None:
			if True:
			#if self.store[treeiter][col_state] in ["done","cancelled","skipped"]:
				try:
					os.remove(OUTPUT_PATTERN.format(self.store[treeiter][col_id]))
				except: pass
				if not self.store.remove(treeiter):
					return
			else:
				treeiter=self.store.iter_next(treeiter)
	
	def joblist_delete(self,widget):
		model, treeiter = self.tree.get_selection().get_selected()
		try:
			os.remove(OUTPUT_PATTERN.format(self.store[treeiter][col_id]))
		except: pass
		self.store.remove(treeiter)
	
	def joblist_cancel(self,widget):
		model, treeiter = self.tree.get_selection().get_selected()
		jobid=model[treeiter][col_id]
		subprocess.call(["scancel",str(jobid)])


	def get_definition_from_name(self,name):
		for defi in self.definitions:
			if defi.infodict["jobname"]==name:
				return defi

	def run_definition(self,widget):
		model, treeiter = self.definition_tree.get_selection().get_selected()
		name=model[treeiter][0]
		defi=self.get_definition_from_name(name)
		scripts=defi.job_scripts()
		for i in range(len(scripts)):
			self.start_job(defi.infodict["jobname"],scripts[i][0],scripts[i][1])
	
	def edit_definition_dialog(self,widget):
		model, treeiter = self.definition_tree.get_selection().get_selected()
		name=model[treeiter][0]
		defi=self.get_definition_from_name(name)
		dialog=JobDescriptionDialog(self,defi)
		result=dialog.run()
		if result==gtk.RESPONSE_OK:
			self.definitions.remove(defi)
			self.definition_store.remove(treeiter)
			if dialog.definition is None:
				raise Exception("definition not set!")
			self.add_definition(dialog.definition)
		dialog.destroy()
	
	def delete_definition(self,widget):
		model, treeiter = self.definition_tree.get_selection().get_selected()
		name=model[treeiter][0]
		defi=self.get_definition_from_name(name)
		self.definitions.remove(defi)
		self.definition_store.remove(treeiter)
	
	def add_definition_dialog(self,widget):
		dialog=JobDescriptionDialog(self)
		result=dialog.run()
		if result==gtk.RESPONSE_OK:
			#print(dialog.__dict__)
			if dialog.definition is None:
				raise Exception("definition not set!")
			self.add_definition(dialog.definition)
		dialog.destroy()
	
	def job_selected(self,selection):
		model,treeiter=selection.get_selected()
		filename=OUTPUT_PATTERN.format(model[treeiter][0])
		state=model[treeiter][col_state]
		self.refresh_output_enabled=self.refresh_enabled and state not in ["done","cancelled","skipped"]
		try:
			with open(filename,"r") as f:
				content=f.read()
			self.outputbuffer.set_text(content)
		except:
			self.outputbuffer.set_text("NO OUTPUTFILE FOUND")
	
	def main(self):
		gtk.main()
	
	def start_job(self,jobname,jobscript,parameters):
		#jobname="testjob"
		#jobscript=template.format(jobname=jobname,mempercpu="1000",numtasks="1",commands="sleep 10",outputfolder=OUTPUT_PATTERN.format("%j"))
		
		p=subprocess.Popen(["sbatch","--"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		out,err=p.communicate(jobscript)
		match=re.search("Submitted batch job (\d+)\n",out)
		if match is None:
			msgbox=gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format=err)
			msgbox.run()
			msgbox.destroy()
			raise Exception("unable to start job: {};{}".format(out,err))
		jobid=int(match.group(1))
		now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		self.add_job_to_list(jobid,now,jobname,parameters)
	
	def set_state(self,row,state,show_notifications):
		oldstate=row[col_state]
		row[col_state]=state
		row[col_color]={"cancelled":"#A0A000","running":"#000000","pending":"#A0A0A0","done":"#00A000","skipped":"#004000","error":"#A00000"}[state]
		if show_notifications and state!=oldstate:
			if state=="done":
				self.notification("Job finished","Job {} has finished!".format(row[col_name]))
			if state=="cancelled":
				self.notification("Job cancelled","Job {} has been cancelled!".format(row[col_name]))
			if state=="error":
				self.notification("ERROR in job","an error occurred in job {}!".format(row[col_name]))
	
	def update_job_list(self,show_notifications=True):
		if not self.refresh_enabled():
			return True
		treeiter = self.store.get_iter_first()
		job_selection=self.tree.get_selection()
		model,selected_job=job_selection.get_selected()
		if selected_job is not None:
			selected_job_id=self.store[selected_job][col_id]
		else:
			selected_job_id=None
		while treeiter != None:
			row=self.store[treeiter]
			state=row[col_state]
			filename=OUTPUT_PATTERN.format(row[col_id])
			def check_state():
				if self.refresh_output_enabled and selected_job_id==row[col_id]:
					self.job_selected(job_selection)	# dirty! - will reload output even for finished jobs!
				if state=="running" or state=="???" or state=="pending":
					try:
						with open(filename,"r") as f:
							outlines=f.readlines()

						for keyword,state_word in [("CANCELLED","cancelled"),("KILLED","error")]:
							try:
								match=re.search("\*\*\* JOB \d+ {}".format(keyword),outlines[-1])
								if match is not None:
									self.set_state(row,state_word,show_notifications)
									return
							except Exception as e:
								print("Error: {}".format(e))

						match=re.search("ERROR",outlines[-1])
						if match is not None:
							self.set_state(row,"error",show_notifications)
							return

						match=re.search("SKIPPED",outlines[-1])
						if match is not None:
							self.set_state(row,"skipped",show_notifications)
							return

						match=re.search("Finished at",outlines[-2])
						if match is not None:
							self.set_state(row,"done",show_notifications)
							return
						self.set_state(row,"running",show_notifications)
					except (IOError,IndexError) as e:
						self.set_state(row,"pending",show_notifications)
			check_state()
			treeiter=self.store.iter_next(treeiter)
		return True
		# iterate over all jobs
		# for jobs still running:
		# check output file for magic end marker or CANCELLED/etc output
	
	def load_job_definitions(self):
		try:
			self.definitions=[]
			with open(DEFINITION_FILE,"r") as f:
				ds=pickle.load(f)
			for d in ds:
				self.add_definition(d)
		except:
			pass
	
	def save_job_definitions(self):
		try:
			with open(DEFINITION_FILE,"w") as f:
				pickle.dump(self.definitions,f)
		except Exception as e:
			print("Error saving job definitions: {}".format(e))
	
	def load_jobs(self):
		try:
			with open(JOBS_FILE,"r") as f:
				rows=pickle.load(f)
			for row in rows:
				self.store.append(row)
		except:
			pass
		
	def save_jobs(self):
		try:
			with open(JOBS_FILE,"w") as f:
				rows=[]
				for row in self.store:
					cells=[]
					for cell in row:
						cells.append(cell)
					rows.append(cells)
				pickle.dump(rows,f)
		except Exception as e:
			print("Error saving job definitions: {}".format(e))
	

	def add_definition(self,desc):
		print("before adding: ",self.definitions)
		for defi in self.definitions:
			d1i=defi.infodict["jobname"]
			d2i=desc.infodict["jobname"]
			if d1i==d2i:
				raise Exception("There is already a job definition with name \"{}\"".format(desc.infodict["jobname"]))
		self.definitions.append(desc)
		self.definition_store.append([desc.infodict["jobname"]])


if __name__=="__main__":
	app=MainWindow()
	app.main()
	if notification_daemon is not None:
		notification_daemon.terminate()

# TODO: clear-button for joblist
# TODO: delete-button for job definitions
