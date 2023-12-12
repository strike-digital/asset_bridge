# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Asset Bridge 2.2.1",
    "author": "Andrew Stevenson",
    "description": "Easily download and import free assets from the internet.",
    "blender": (4, 0, 0),
    "version": (2, 2, 1),
    "location": "3D View > N-Panel > Asset Bridge",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

from . import auto_load
from . import addon_updater_ops

auto_load.init()


def register():
    auto_load.register()
    addon_updater_ops.register(bl_info)


def unregister():
    auto_load.unregister()
    addon_updater_ops.unregister()
