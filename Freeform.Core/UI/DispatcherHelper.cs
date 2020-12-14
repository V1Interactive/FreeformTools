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

namespace Freeform.Core.UI
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using System.Text;
    using System.Threading.Tasks;
    using System.Windows.Threading;


    public static class DispatcherHelper
    {
        /* Code pulled from MVVM Light's DispatcherHelper class and simplified for our needs
         * 
         * Helper class to store a UI's Dispatcher so that it can be called in MVVM structure to update the UI
         * from a non-UI thread.
         */
        public static Dispatcher UIDispatcher;

        public static void CheckBeginInvokeOnUI(Action action)
        // ReSharper restore InconsistentNaming
        {
            if (action == null)
            {
                return;
            }

            CheckDispatcher();

            if (UIDispatcher.CheckAccess())
            {
                action();
            }
            else
            {
                UIDispatcher.BeginInvoke(action);
            }
        }


        private static void CheckDispatcher()
        {
            if (UIDispatcher == null)
            {
                var error = new StringBuilder("The DispatcherHelper is not initialized.");
                error.AppendLine();
                throw new InvalidOperationException(error.ToString());
            }
        }
    }
}
