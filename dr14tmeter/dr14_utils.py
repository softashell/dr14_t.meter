
# dr14_t.meter: compute the DR14 value of the given audiofiles
# Copyright (C) 2011  Simone Riva
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
    

import os
import argparse
import time
import multiprocessing
from dr14tmeter.dynamic_range_meter import DynamicRangeMeter
from dr14tmeter.database import dr_database, dr_database_singletone
from dr14tmeter.table import *
from dr14tmeter.audio_analysis import *
from dr14tmeter.dr14_global import *
from dr14tmeter.dr14_config import *

import subprocess
import sys
import re
import tempfile
from dr14tmeter.out_messages import print_msg
import fileinput


def scan_files_list( input_file , options , out_dir ):
    
    success = False
    r = 0 ;
    
    if out_dir == None:
        out_dir = tempfile.gettempdir()
    else:
        out_dir = os.path.abspath( out_dir )
    
    a = time.time()
    
    if input_file == None:
        input_file = '-'
    
    files_list = []
    
    for line in fileinput.input( input_file ):
        files_list.append( os.path.abspath( line.rstrip() ) )
        
    dr = DynamicRangeMeter()
    dr.write_to_local_db( db_is_enabled() )
    
    r = dr.scan_mp( files_list=files_list , thread_cnt=get_thread_cnt() )
    
    if r == 0:
        success = False
    else:
        write_results( dr , options , out_dir , "" )
        success = True
    
    clock = time.time() - a
    return (success,clock,r)
    

def scan_dir_list( subdirlist , options , out_dir ):
    a = time.time()

    success = False

    for cur_dir in subdirlist :
        dr = DynamicRangeMeter()
        dr.write_to_local_db( db_is_enabled() )
        
        print_msg ( "\n------------------------------------------------------------ " )		        
        print_msg ( "> Scan Dir: %s \n" % cur_dir )
        
        cpu = multiprocessing.cpu_count()
                
        if ( options.disable_multithread == True ) :
            r = dr.scan_dir( cur_dir )
        else:
            cpu = get_thread_cnt()
                
            r = dr.scan_mp( cur_dir , cpu )
            
        if r == 0:
            continue
        else:
            success = True
            
        write_results( dr , options , out_dir , cur_dir )        
         
    
    clock = time.time() - a
    
    return (success,clock,r)


def get_thread_cnt():
    cpu = multiprocessing.cpu_count()
    cpu = cpu / 2
    if cpu <= 2:
        cpu = 2
    else:
        cpu = int( round( cpu ) )
    return cpu


def list_rec_dirs( basedir , subdirlist=None ):
    
    if subdirlist == None :
        subdirlist = []
        subdirlist.append( basedir )
        

    for item in os.listdir( basedir ):
        item = os.path.join( basedir , item )
        if os.path.isdir( item ):
            item = os.path.abspath( item )
            #print_msg( item )
            subdirlist.append( item )
            list_rec_dirs( item , subdirlist )
            
    return subdirlist
        

def write_results( dr , options , out_dir , cur_dir ) :
    out_list = "" ;
   
    table_format = not( options.basic_table )    
    
    if out_dir == None :
        full_out_dir = os.path.join( cur_dir )
    else :
        full_out_dir = out_dir
    
    print_msg( "DR = " + str( dr.dr14 ) )
    
    if not ( os.access( full_out_dir , os.W_OK ) ) :
        full_out_dir = tempfile.gettempdir() ; 
        print_msg( "--------------------------------------------------------------- " )
        print_msg( "- ATTENTION !" )
        print_msg( "- You don't have the write permission for the directory: %s " % full_out_dir )
        print_msg( "- The result files will be written in the tmp dir: %s " % full_out_dir )
        print_msg( "--------------------------------------------------------------- " )
           
    
    if options.print_std_out :
        dr.fwrite_dr( "" , TextTable() , table_format , True )
        
    if options.turn_off_out :
        return 
    
    all_tables = False
    if 'a' in options.out_tables:
        all_tables = True 
    
    tables_list = { 'b' : ["dr14_bbcode.txt",BBcodeTable()] , 't' : ["dr14.txt",TextTable()]  ,
        'h' : ["dr14.html",HtmlTable()] , 'w' : ["dr14_mediawiki.txt",MediaWikiTable()] }
    
    out_list = ""
    
    
    for code in tables_list.keys():
        if code in options.out_tables or all_tables :
            dr.fwrite_dr( os.path.join( full_out_dir , tables_list[code][0] ) , tables_list[code][1] , table_format , append=options.append , dr_database=options.dr_database )
            out_list = out_list + " %s " % tables_list[code][0]
            
    
    print_msg("")
    print_msg("- The full result has been written in the files: %s" % out_list )
    print_msg("- located in the directory: ")
    print_msg( full_out_dir )
    print_msg("")


def test_path_validity( path ):
    if path in [ "/" , "" ]:
        return False
    if os.access( path , os.W_OK ):
        return True
    else :
        ( h , t ) = os.path.split( path )
        return test_path_validity( h )
    return False


def local_dr_database_configure():
    
    subprocess.call( "clear" , shell=True )
    
    print_out( "---------------------------------------------------------------------------------------------- " )
    print_out( "- DR14 T.meter --  " )
    print_out( "- Local DR database - Configuration procedure " )
    print_out( "---------------------------------------------------------------------------------------------- " )
    
    print_out( "  " )
    print_out( "  The database, if enabled, automatically stores all DR result in a local database " )
    print_out( "  - You must set up some parameters to use the database -" )
    print_out( "  " )    
    
    flag = True
    while flag :
        print_out( "  1. Insert the database directory: Default [%s]:" % os.path.split( get_db_path() )[0] )
        db_path = input("     > ")
        db_path = os.path.expanduser( db_path )
        db_path = os.path.expandvars( db_path )
        
        if re.sub( "\s+" , "" , db_path ) == "" :
            flag = False
            db_path = os.path.split( get_db_path() )[0]
            continue
        
        db_path = os.path.abspath( db_path )
        
        if test_path_validity( db_path ) :
            flag = False
        else :
            print_out( "  - [ %s ] is not a directory, please insert an acceptable directory name" % db_path )
    
    print_out( "  " )
    print_out( "---------------------------------------------------------------------------------------------- " )
    print_out( "  " )
    print_out( "     If you set a collection directory ONLY the tracks inside this base folder and sub-folders " )
    print_out( "     will be added to the database." )
    print_out( "     If you insert \'any\' all analyzed tracks will be added to the database " )
    
    flag = True
    while flag :
        print_out( "  2. Insert your collection directory: Dafault [%s] " % "any" )
        coll_path = input("     > ")
        coll_path = os.path.expanduser( coll_path )
        coll_path = os.path.expandvars( coll_path )
        
        if re.sub( "(\s+)" , "" , coll_path ) in [ "" , "any" ] :
            flag = False
            coll_path = "/"
            continue 
            
        coll_path = os.path.abspath( coll_path )
        
        if os.path.isdir( coll_path ) :
            flag = False
        else :
            print_out( "  - [ %s ] is not a directory, please insert an existing directory name" % coll_path )
    
    print_out( "  " )
    print_out( "---------------------------------------------------------------------------------------------- " )
        
    return ( db_path , coll_path )
    
def print_query_help():
    print_msg( "query help" )

def exec_limited_query( options , qf ):
            
    if len( options.query ) == 1 :
        limit = 30 
    else :
        try:
            limit = int( float( options.query[1] ) )
        except ValueError:
             limit = 30
             
    (res_dict, keys) = qf( limit=limit )

    return (res_dict, keys)
    
    
def database_exec_query( options ):
    ## [ "help" , "top" , "worst" , "hist" , "evol" ]
    
    res_dl = [{}]
    db = dr_database_singletone().get()
    
    if options.query[0] == "help" :
        print_query_help()
        return
    
    elif options.query[0] == "top" :
        table_title = "Top DR tracks"
        (res_dl, keys) = exec_limited_query( options , db.query_top_dr )
        
    elif options.query[0] == "worst" :
        table_title = "Worst DR Tracks"
        (res_dl, keys) = exec_limited_query( options , db.query_worst_dr )  
        
    elif options.query[0] == "hist" :
        table_title = "DR histogram"
        (res_dl, keys) = db.query_dr_histogram()
        
    elif options.query[0] == "evol" :
        table_title = "DR evolution"
        (res_dl, keys) = db.query_date_evolution()
        
    wr = WriteDr()        
    tm = TextTable() 
    table_code = wr.write_query_result( res_dl , tm , table_title , keys )
    print_out( table_code )


def run_analysis_opt( options , path_name ):
    
    flag = False
    
    if options.compress:
        
        if test_compress_modules() == False :
            sys.exit(1)
        
        print_msg("Start compressor:")
        comp = AudioCompressor()
        comp.setCompressionModality( options.compress )
        comp.compute_track( path_name )
        flag = True
        
    
    if options.spectrogram:
        
        if test_matplotlib_modules( "Spectrogram" ) == False:
            sys.exit(1)
        
        print_msg("Start spectrogram:")
        spectr = AudioSpectrogram()
        spectr.compute_track( path_name )
        flag = True

    if options.plot_track:
        
        if test_matplotlib_modules( "Plot track" ) == False:
            sys.exit(1)
        
        print_msg("Start Plot Track:")
        spectr = AudioPlotTrack()
        spectr.compute_track( path_name )
        flag = True

    if options.plot_track_dst:
        
        if test_matplotlib_modules( "Plot track dst" ) == False:
            sys.exit(1)
        
        print_msg("Start Plot Track:")
        spectr = AudioPlotTrackDistribution()
        spectr.compute_track( path_name )
        flag = True

    if options.histogram:
        
        if test_hist_modules() == False:
            sys.exit(1)
        
        print_msg("Start histogram:")
        hist = AudioDrHistogram()
        hist.compute_track( path_name )
        flag = True

    if options.lev_histogram:
        
        if test_hist_modules() == False:
            sys.exit(1)
        
        print_msg("Start level histogram:")
        hist = AudioLevelHistogram()
        hist.compute_track( path_name )
        flag = True
    
        
    if options.dynamic_vivacity :
        if test_hist_modules() == False:
            sys.exit(1)
        
        print_msg("Start Dynamic vivacity:")
        viva = AudioDynVivacity()
        viva.compute_track( path_name )
        flag = True
        
    return flag
