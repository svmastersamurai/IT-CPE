#!/usr/bin/python
"""These are the org-specific AutoDMG package building tools."""

import os
import glob
import tempfile
import shutil

from autodmg_utility import build_pkg, run, pkgbuild
try:
  import FoundationPlist as plistlib
except ImportError:
  print "Using plistlib"
  import plistlib


# global DESTINATION
DESTINATION = '/Library/AutoDMG'

# Sample package construction list
# Each dict contains the information necessary to build a package from a given
# source, with receipt and file name, and potentially a target.
PKG_LIST = [
  # Wallpapers are present at image time
  {
    'pkg_name': 'cpe_wallpapers',
    'source': '/Users/Shared/Wallpapers',
    'receipt': 'com.facebook.cpe.wallpapers',
    'comment': 'Building Wallpapers package'
  },
  # Suppress Diagnostics prompt
  {
    'pkg_name': 'suppress_diagnostics',
    'source': '/Library/AutoDMG/additions/diagnostics',
    'receipt': 'com.facebook.cpe.suppress_diagnostics',
    'comment': 'Building Diagnostic Suppression package',
    'target': '/Library/Application Support/CrashReporter'
  },
]


# Convenient functions
def get_system_version(sys_root):
  """Get the version and build number from a system root."""
  system_version_plist = os.path.join(
    sys_root,
    'System',
    'Library',
    'CoreServices',
    'SystemVersion.plist',
  )
  sys_version_data = plistlib.readPlist(system_version_plist)
  return (
    sys_version_data['ProductVersion'],
    sys_version_data['ProductBuildVersion']
  )


def get_version_from_os_dmg(dmg_path):
  """Get a system version from an OS dmg."""
  (version, build) = (0, 0)
  if os.path.isfile(dmg_path):
    print "Mounting %s" % dmg_path
    mountpoints = fs_tools.mountdmg(dmg_path)
    if mountpoints:
      (version, build) = get_system_version(mountpoints[0])
      print "Found %s: %s" % (version, build)
      print "Umounting dmg"
      fs_tools.unmountdmg(mountpoints[0])
      print "Done unmounting."
  return (version, build)


# Other DMG builds
def build_bare_dmg(source, cache, logpath, loglevel, repo_path):
  """Build a base OS DMG."""
  dmg_output_path = os.path.join(cache, 'Base.hfs.dmg')
  print "Looking for existing base image..."
  base_os_dmg_matches = glob.glob(os.path.join(cache, 'Base*.hfs.dmg'))
  (my_os_version, my_build) = get_system_version('/')
  for os_dmg in base_os_dmg_matches:
    (dmg_version, dmg_build) = get_version_from_os_dmg(os_dmg)
    if dmg_version == my_os_version and dmg_build == my_build:
      # The DMG we have built already matches.
      print "Matching version base image already found, not building.\n"
      return
  print "Creating AutoDMG-bare.adtmpl."
  templatepath = os.path.join(cache, 'AutoDMG-bare.adtmpl')
  plist = dict()
  plist["ApplyUpdates"] = True
  plist["SourcePath"] = source
  plist["TemplateFormat"] = "1.0"
  plist["VolumeName"] = "Macintosh HD"
  # Complete the AutoDMG-donation.adtmpl template
  plistlib.writePlist(plist, templatepath)
  autodmg_cmd = [
    '/Applications/AutoDMG.app/Contents/MacOS/AutoDMG'
  ]
  if os.getuid() == 0:
    # We are running as root
    print "Running as root."
    autodmg_cmd.append('--root')

  logfile = os.path.join(logpath, 'bare.log')

  # Now kick off the AutoDMG build
  print "Building base image..."
  if os.path.isfile(dmg_output_path):
    os.remove(dmg_output_path)
  cmd = autodmg_cmd + [
    '-L', loglevel,
    '-l', logfile,
    'build', templatepath,
    '--download-updates',
    '-o', dmg_output_path]
  run(cmd)
  if os.path.exists(dmg_output_path):
    print "Copying base image to DS Repo."
    repo_hfs = os.path.join(repo_path, 'Masters', 'HFS')
    shutil.copy2(dmg_output_path, repo_hfs)
    target_name = "Base_%s.%s.hfs.dmg" % (my_os_version, my_build)
    os.rename(dmg_output_path, os.path.join(cache, target_name))
  else:
    print "Failed to build base image!"


# local management functions
def munki_bootstrap(cache_path):
  """Build a Munki bootstrap package."""
  pkg_output_file = os.path.join(cache_path, 'munki_bootstrap.pkg')
  if not os.path.isfile(pkg_output_file):
    print "Building Munki bootstrap package..."
    temp_dir = tempfile.mkdtemp(prefix='munkiboot', dir='/tmp')
    shared = os.path.join(temp_dir, 'Users/Shared')
    os.makedirs(shared)
    open(os.path.join(
      shared, '.com.googlecode.munki.checkandinstallatstartup'
    ), 'a').close()
    pkgbuild(
      temp_dir,
      'com.facebook.cpe.munki.bootstrap',
      '1.0',
      pkg_output_file
    )
    shutil.rmtree(temp_dir, ignore_errors=True)
    if os.path.isfile(pkg_output_file):
      return pkg_output_file
    # If we failed for some reason, return None
    return None
  # Package already exists
  return pkg_output_file


def suppress_registration(cache_path):
  """Build a package to suppress Setup Assistant, returns path to it."""
  pkg_output_file = os.path.join(cache_path, 'suppress_registration.pkg')
  if not os.path.isfile(pkg_output_file):
    print "Building registration suppression package..."
    temp_dir = tempfile.mkdtemp(prefix='suppressreg', dir='/tmp')
    receipt = os.path.join(temp_dir, 'Library/Receipts')
    os.makedirs(receipt)
    open(os.path.join(receipt, '.SetupRegComplete'), 'a').close()
    vardb = os.path.join(temp_dir, 'private/var/db/')
    os.makedirs(vardb)
    open(os.path.join(vardb, '.AppleSetupDone'), 'a').close()
    pkgbuild(
      temp_dir,
      'com.facebook.cpe.suppress_registration',
      '1.0',
      pkg_output_file
    )
    shutil.rmtree(temp_dir, ignore_errors=True)
    if os.path.isfile(pkg_output_file):
      return pkg_output_file
    # If we failed for some reason, return None
    return None
  # Package already exists
  return pkg_output_file


def run_unique_code(args):
  """Run any special code or builds.

  Arguments from the script are passed in.
  Return a list of any packages you want included in the additions.
  """
  pkg_list = []
  # EXAMPLE ORGANIZATION-UNIQUE CODE:
  # Perhaps you want to build a bunch of extra packages to include.
  # You could use the PKG_LIST list above to set up your package building.
  # ********
  # for package in PKG_LIST:
  #   pkg_list.append(
  #     build_pkg(
  #       package['source'],
  #       package['pkg_name'],
  #       package['receipt'],
  #       package.get('target', package['source']),
  #       DESTINATION,
  #       package['comment']
  #     )
  #   )
  # Each package needs to be added to the pkg_list to be returned,
  # so it can be added to the overall additions list.
  # ********
  # EXAMPLE CUSTOM PACKAGE FUNCTIONS
  # You can create your own functions for building packages, and
  # include those too. Append each package to pkg_list:
  # ********
  # registration_pkg = suppress_registration(args.cache)
  # if registration_pkg:
  #   pkg_list.append(registration_pkg)
  # munki_bootstrap_pkg = munki_bootstrap(args.cache)
  # if munki_bootstrap_pkg:
  #   pkg_list.append(munki_bootstrap_pkg)
  # ********
  # EXAMPLE BARE IMAGE:
  # If you want to build your own bare/thin image, using just the OS,
  # use the build_bare_dmg() function:
  # ********
  # build_bare_dmg(args.source, args.cache, args.logpath,
  #                str(args.loglevel), args.dsrepo)
  # ********
  return pkg_list

if __name__ == '__main__':
  run_unique_code({})
