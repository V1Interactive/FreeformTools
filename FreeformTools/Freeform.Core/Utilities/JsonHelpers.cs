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
    using System.IO;
    using Newtonsoft.Json;

    public static class JsonHelpers
    {
        public static void WriteJsonFile(string fullpath, object data)
        {
            var json = JsonConvert.SerializeObject(data, Formatting.Indented);
            File.WriteAllText(fullpath, json);
        }

        public static dynamic ReadJsonData(string fullpath)
        {
            var serializer = new JsonSerializer();
            using (var sr = new StreamReader(fullpath))
            using (var reader = new JsonTextReader(sr))
            {
                return serializer.Deserialize<dynamic>(reader);
            }
        }

        public static T LoadFile<T>(string fullpath)
        {
            if (!File.Exists(fullpath))
            {
                return default(T);
            }

            using (var stream = new StreamReader(fullpath))
            using (var reader = new JsonTextReader(stream))
            {
                var serializer = new JsonSerializer();
                return serializer.Deserialize<T>(reader);
            }
        }

    }
}