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

namespace Freeform.Core.Network
{
    using System.Linq;
    using System.Net;
    using System.Net.NetworkInformation;
    using System.Net.Sockets;

    public class NetworkHost
    {
        public string Hostname { get; set; }

        public string IpAddress { get; set; }

        public string Name => this.Hostname;

        public static bool CanConnect(string host)
        {
            var h = new NetworkHost { Hostname = host };
            return h.CanConnect();
        }

        public bool CanConnect()
        {
            try
            {
                var entry = Dns.GetHostEntry(this.Hostname);

                if (entry.AddressList.Length == 0)
                {
                    return false;
                    //throw new SensorException(this, SensorCode.Failure, $"No addresses found for {this.Hostname}.");
                }

                if (!string.IsNullOrEmpty(this.IpAddress))
                {
                    var address = entry.AddressList[0].ToString();
                    if (entry.AddressList.All(a => this.IpAddress != a.ToString()))
                    {
                        return false;
                        //throw new SensorException(this, SensorCode.Failure, $"Host {this.Hostname} not found.");
                    }
                }

                var ping = new Ping();
                var ret = ping.Send(this.Hostname, 2500);
                if (ret.Status != IPStatus.Success)
                {
                    return false;
                    //throw new SensorException(this, SensorCode.Failure, $"Failed to ping host {this.Hostname}, {ret.Status}.");
                }

                return true;
            }
            catch (SocketException)
            {
                return false;
                //throw new SensorException(this, SensorCode.Failure, $"Host {this.Hostname} not found ({ex.Message}).");
            }
        }
    }
}