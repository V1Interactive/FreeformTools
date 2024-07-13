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

namespace Freeform.Core.Helpers
{
    using System;
    using System.Collections.Specialized;
    using System.Net;
    using System.Text;
    using Newtonsoft.Json;

    public class SlackClient
    {
        private readonly Uri uri;
        private readonly Encoding encoding = new UTF8Encoding();

        public string AccessToken { get; set; }

        public SlackClient(string urlWithAccessToken)
        {
            this.uri = new Uri(urlWithAccessToken);
        }

        //Post a message using simple strings
        public void PostMessage(string text, string username = null, string channel = null)
        {
            var payload = new Payload()
            {
                Channel = channel,
                Username = username,
                Text = text
            };

            this.PostMessage(payload);
        }

        //Post a message using a Payload object
        public void PostMessage(Payload payload)
        {
            var payloadJson = JsonConvert.SerializeObject(payload);

            using (var client = new WebClient())
            {
                var data = new NameValueCollection();
                data["payload"] = payloadJson;

                var response = client.UploadValues(this.uri, "POST", data);

                //The response text is usually "ok"
                var responseText = this.encoding.GetString(response);
            }
        }

        public void PostMessage(string message)
        {
            var urlWithAccessToken = $"https://v1interactive.slack.com/services/hooks/incoming-webhook?token={this.AccessToken}";

            var client = new SlackClient(urlWithAccessToken);

            client.PostMessage("Slackbox", message, "#bamoo");
        }
    }

    //This class serializes into the Json payload required by Slack Incoming WebHooks
    public class Payload
    {
        [JsonProperty("channel")]
        public string Channel { get; set; }

        [JsonProperty("username")]
        public string Username { get; set; }

        [JsonProperty("text")]
        public string Text { get; set; }
    }
}