/*
 * Freeform Rigging and Animation Tools
 * Copyright (C) 2020  Micah Zahm
 *
 * Freeform Rigging and Animation Tools is free software: you can redistribute it 
 * and/or modify it under the terms of the GNU General Public License as published 
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Freeform Rigging and Animation Tools is distributed in the hope that it will 
 * be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Freeform Rigging and Animation Tools.  
 * If not, see <https://www.gnu.org/licenses/>.
 */
 
namespace Freeform.Core.Utilities
{
    using System;
    using System.IO;
    using System.Linq;
    using System.Reflection;
    using Microsoft.Win32;

    public static class PathHelper
    {
        public static string GetApplicationFile(string filename, System.Environment.SpecialFolder folder = System.Environment.SpecialFolder.LocalApplicationData)
        {
            var appPath = GetApplicationFolder(folder);
            var fullPath = Path.Combine(appPath, filename);
            return fullPath;
        }

        public static string GetApplicationFile(string appTitle, string filename, System.Environment.SpecialFolder folder = System.Environment.SpecialFolder.LocalApplicationData)
        {
            var appPath = GetApplicationFolder(appTitle, folder);
            var fullPath = Path.Combine(appPath, filename);
            return fullPath;
        }

        public static string GetApplicationFolder(System.Environment.SpecialFolder folder = System.Environment.SpecialFolder.LocalApplicationData)
        {
            var assembly = Assembly.GetEntryAssembly() ?? Assembly.GetExecutingAssembly();
            var appTitle = assembly.GetCustomAttributes(typeof(AssemblyTitleAttribute), false)
                    .OfType<AssemblyTitleAttribute>()
                    .First()
                    .Title;
            return GetApplicationFolder(appTitle, folder);
        }

        public static string GetApplicationFolder(string appTitle, System.Environment.SpecialFolder folder = System.Environment.SpecialFolder.LocalApplicationData)
        {
            var systemPath = System.Environment.GetFolderPath(folder);
            var appPath = Path.Combine(systemPath, appTitle);
            Directory.CreateDirectory(appPath);
            return appPath;
        }

        public static string CreateTempFolder(string prefix)
        {
            var folder = $@"{prefix}-{Guid.NewGuid()}";
            var fullpath = Path.Combine(Path.GetTempPath(), folder);
            return fullpath;
        }

        public static string GetTempFileName(string extension)
        {
            var fileName = Path.GetTempPath() + Guid.NewGuid() + extension;
            return fileName;
        }

        public static string GetTempFileName(string prefix, string extension)
        {
            var filename = $@"{prefix}-{Guid.NewGuid()}{extension}";
            var fullpath = Path.Combine(Path.GetTempPath(), filename);
            return fullpath;
        }

        public static char PathSeparator = '\\';

        public static string Normalize(string fullpath)
        {
            if (string.IsNullOrEmpty(fullpath))
            {
                return fullpath;
            }

            var result = fullpath.Replace('/', PathSeparator); // normalize to WINDOWS path
            result = result[0] + result.Substring(1).Replace(@"\\", @"\");

            if (result.EndsWith($"{PathSeparator}"))
            {
                return result.TrimEnd(PathSeparator);
            }

            return result;
        }

        private static string NormalizeInternal(string fullpath)
        {
            var result = Normalize(fullpath);
            return result.ToLowerInvariant();
        }

        public static bool AreEqual(string a, string b)
        {
            var na = Normalize(a).ToLower();
            var nb = Normalize(b).ToLower();
            return 0 == string.Compare(na, nb);
        }

        public static bool PathIsChild(string root, string child)
        {
            root = NormalizeInternal(root);
            child = NormalizeInternal(child);
            return child.StartsWith(root);
        }
    }
}