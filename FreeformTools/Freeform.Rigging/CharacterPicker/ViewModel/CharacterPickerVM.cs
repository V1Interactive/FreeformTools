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

namespace Freeform.Rigging.CharacterPicker
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.Linq;
    using System.Windows.Controls;
    using System.Windows.Data;
    using System.Windows.Forms;
    using Freeform.Core.UI;

    class CharacterPickerVM : ViewModelBase
    {
        public event EventHandler ImportRigsEventHandler;

        public RelayCommand ImportRigsCommand { get; set; }

        string _windowTitle;
        public string WindowTitle
        {
            get { return _windowTitle; }
            set
            {
                if (_windowTitle != value)
                {
                    _windowTitle = value;
                    RaisePropertyChanged("WindowTitle");
                }
            }
        }

        string _importText;
        public string ImportText
        {
            get { return _importText; }
            set
            {
                if(_importText != value)
                {
                    _importText = value;
                    RaisePropertyChanged("ImportText");
                }
            }
        }

        string _selectionMode;
        public string SelectionMode
        {
            get { return _selectionMode; }
            set
            {
                if (_selectionMode != value)
                {
                    _selectionMode = value;
                    RaisePropertyChanged("SelectionMode");
                }
            }
        }


        ObservableCollection<RigFile> _rigList;
        public ObservableCollection<RigFile> RigList
        {
            get { return _rigList; }
            set
            {
                if (_rigList != value)
                {
                    _rigList = value;
                    RaisePropertyChanged("RigList");
                }
            }
        }


        public CollectionViewSource RigListViewSource { get; set; }
        string _rigFilter;
        public string RigSearchFilter
        {
            get { return _rigFilter; }
            set
            {
                _rigFilter = value;
                if (!string.IsNullOrEmpty(_rigFilter))
                    AddRegionFilter();

                RigListViewSource.View.Refresh();

                if (!RigListViewSource.View.IsEmpty)
                {
                    var enumerator = RigListViewSource.View.GetEnumerator();
                    enumerator.MoveNext();
                }
            }
        }


        public List<RigFile> SelectedRigList;
        readonly RigFile _selectedRigItem;
        public RigFile SelectedRigItem
        {
            get { return _selectedRigItem; }
            set
            {
                if (_selectedRigItem != value)
                {
                    // Don't set _selectedRigItem so it stays null for the UI to think the selection is always changed with Extended selection
                    SelectedRigList = RigList.Cast<RigFile>().Where(x => x.IsSelected).ToList();
                    RaisePropertyChanged("SelectedRigItem");
                }
            }
        }


        public CharacterPickerVM()
        {
            WindowTitle = "Picker";
            ImportText = "Import Rigs";
            SelectionMode = "Extended";

            _selectedRigItem = null;
            RigList = new ObservableCollection<RigFile>();
            RigListViewSource = new CollectionViewSource
            {
                Source = RigList
            };
            RigListViewSource.SortDescriptions.Add(new SortDescription("FileName", ListSortDirection.Ascending));

            ImportRigsCommand = new RelayCommand(ImportRigsCall);
        }

        void ImportRigsCall(object sender)
        {
            ImportRigsEventArgs eventArgs = new ImportRigsEventArgs()
            {
                ImportList = SelectedRigList
            };
            ImportRigsEventHandler?.Invoke(this, eventArgs);
        }


        private void AddRegionFilter()
        {
            RigListViewSource.Filter -= new FilterEventHandler(RigsFilter);
            RigListViewSource.Filter += new FilterEventHandler(RigsFilter);
        }

        private void RigsFilter(object sender, FilterEventArgs e)
        {
            e.Accepted = false;

            if (string.IsNullOrEmpty(RigSearchFilter))
                e.Accepted = true;

            string[] rigSearchSplit = RigSearchFilter.Split(null);
            string first = rigSearchSplit[0].ToLower();
            string second = string.Empty;
            if (rigSearchSplit.Length > 1)
                second = rigSearchSplit[1].ToLower();


            if (e.Item is RigFile src && e.Accepted == false)
            {
                if (src.FileName.ToLower().Contains(first) ||
                    (src.FullPath.ToLower().Contains(first) && src.FileName.ToLower().Contains(second)))
                {
                    e.Accepted = true;
                }
            }
        }


        public class ImportRigsEventArgs : EventArgs
        {
            public List<RigFile> ImportList = new List<RigFile>();
        }
    }
}
