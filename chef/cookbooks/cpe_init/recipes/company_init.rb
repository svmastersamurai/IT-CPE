#
# Cookbook Name:: cpe_init
# Recipe:: company_init
#
# vim: syntax=ruby:expandtab:shiftwidth=2:softtabstop=2:tabstop=2
#
# Copyright (c) 2016-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#

# HERE: This is where you would set attributes that are consumed by the API
# cookbooks.
node.default['organization'] = 'MYCOMPANY'
node.default['cpe_launchd']['prefix'] = 'com.MYCOMPANY.chef'
node.default['cpe_profiles']['prefix'] = 'com.MYCOMPANY.chef'
